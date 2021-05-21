from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from flask import Flask, redirect, url_for, render_template, request, flash
from square_won_logic import Main, updater
import time
from selenium import webdriver
import sqlite3 as sq
import os, os.path
#this access API on server start and makes a list of the top 10 coins
# TODO: make this an importable script which gives the list as return value
url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
parameters = {
  'start':'1',
  'limit':'10',
  'convert':'USD'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': 'ddd95280-6cce-4605-af4e-f3ada6775e01',
}

session = Session()
session.headers.update(headers)

try:
  response = session.get(url, params=parameters)
  data = json.loads(response.text)
except (ConnectionError, Timeout, TooManyRedirects) as e:
  print(e)

#makes list of coin symbols for use in API fetch
coins = []
for i in range(10):
    coin = data['data'][i]['symbol']
    coins.append(coin)

joined_coins = ','.join(coins)

#Create the sql database
file = str(os.path.abspath(os.getcwd() + '\squarewon.db'))
con = sq.connect(file)

cur = con.cursor()
#check if exists and drop at beginning of server boot
if os.path.exists(file):
    cur.execute('DROP TABLE players')
#creates table
sql_create = 'CREATE TABLE players(name TEXT,email TEXT, {0} FLOAT, {1} FLOAT, {2} FLOAT, {3} FLOAT, {4} FLOAT, {5} FLOAT, {6} FLOAT, {7} FLOAT, {8} FLOAT, {9} FLOAT)'.format(coins[0],coins[1],coins[2],coins[3],coins[4],coins[5],coins[6],coins[7],coins[8],coins[9])
cur.execute(sql_create)
con.commit()
con.close()

#main program starts
app = Flask(__name__)
app.secret_key = 'random string'

#baked in info, only need to change in one place
num_of_5_min_refresh = 3

rowIDs = []
all_players_bets = []

#api baked in info for HTML_start
parameters_CMC_API = {
  'symbol':str(joined_coins)
}
headers_CMC_API = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': 'ddd95280-6cce-4605-af4e-f3ada6775e01',
}

# TODO: REMOVE API KEY AND BACK UP SOMEWHERE

session = Session()
session.headers.update(headers_CMC_API)
url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'

#home is screen used by selenium to update existing values
@app.route('/home')
def home():
    updater(coins, rowIDs, parameters_CMC_API, headers_CMC_API, 'no')
    return render_template('HTML_table.html')

@app.route('/reroute')
def reroute():
    browser = webdriver.Chrome()
    browser.get('http://127.0.0.1:5000/home')
    for cycles in range(num_of_5_min_refresh):
        time.sleep(10)
        browser.refresh()
    browser.close()
    return redirect(url_for('winner'))

@app.route('/winner')
def winner():
    info = updater(coins, rowIDs, parameters_CMC_API, headers_CMC_API, 'yes')

    winner_total = info['Total USD']
    winner_growth = round((winner_total-1000),2)
    winner_growth_percent = round(((winner_total-1000)/1000) * 100,3)
    #return html template of winner temp
    return render_template('HTML_winner.html', name=info['name'], profit=winner_growth, percent=winner_growth_percent)


@app.route('/start', methods=['GET','POST'])
def start():
    #if a button is pressed
    if request.method == 'POST':
        if 'next bet' in request.form:
            #checks to make sure every bet is equal to 1000 USD
            bet_list = []
            for i, coin in enumerate(coins):
                coin_num = 'coin'+ str(i)
                bet = int(request.form[coin_num])
                bet_list.append(bet)
            total_bet_amount = sum(bet_list)

            if total_bet_amount == 1000:
                name = request.form['name']
                email = request.form['email']
                con = sq.connect(file)
                cur = con.cursor()
                #if name list is empty
                if name == 'Name':
                    flash('Please enter a name')
                    return redirect(url_for('start'))
                #if this is first run and name list empty
                if rowIDs == [] or name not in rowIDs:
                    # TODO: add name and bet into HERE to sql database
                    rowIDs.append(name)
                    bet_list = []
                    # TODO: This entire loop can be a function
                    #goes through list of coins accessed by api, makes dict with
                    #the crypto and value of bet placed
                    for i, coin in enumerate(coins):
                        coin_num = 'coin'+ str(i)
                        bet = int(request.form[coin_num])
                        bet_list.append(bet)
                    sql_insert_bet = 'INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?)'
                    val = (name, email, bet_list[0],bet_list[1],bet_list[2],bet_list[3],bet_list[4],bet_list[5],bet_list[6],bet_list[7],bet_list[8],bet_list[9])
                    cur.execute(sql_insert_bet, val)
                    con.commit()
                    con.close()
                    return redirect(url_for('start'))
                else:
                #if not empty
                    if name in rowIDs:
                        #if name is already used with bet
                        flash(f'{name} is already used with bet, please use different name')
                        return redirect(url_for('start'))
            else:
                flash('enter a total of $1000')
                return redirect(url_for('start'))

        elif 'done' in request.form:
            name = request.form['name']
            if rowIDs == []:
                flash('No bets have been entrered')
                return redirect(url_for('start'))
            if name != 'Name':
                flash('Make sure to press Submit bet to enter your bet ')
                return redirect(url_for('start'))
            else:
                Main(coins, rowIDs, parameters_CMC_API, headers_CMC_API)
                return redirect(url_for('reroute'))
    else:
        #main place bets screen
        response = session.get(url, params=parameters_CMC_API)
        data = json.loads(response.text)
        coins_USD = []
        for coin in coins:
            coin_usd = round(data['data'][coin][0]['quote']['USD']['price'], 3)
            coins_USD.append(coin_usd)

        return render_template('ind_start.html', coin0=coins[0], coin1=coins[1],coin2=coins[2],coin3=coins[3],
        coin4=coins[4],coin5=coins[5],coin6=coins[6],coin7=coins[7],coin8=coins[8],coin9=coins[9],
        coin0_USD=coins_USD[0],coin1_USD=coins_USD[1],coin2_USD=coins_USD[2],
        coin3_USD=coins_USD[3],coin4_USD=coins_USD[4],coin5_USD=coins_USD[5],
        coin6_USD=coins_USD[6],coin7_USD=coins_USD[7],coin8_USD=coins_USD[8],coin9_USD=coins_USD[9])

#, use_reloader=True
if __name__ == '__main__':
    app.run(debug=True)
