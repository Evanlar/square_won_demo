from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import pprint
from tabulate import tabulate
import time
import logging
import sqlite3 as sq
import os, os.path
import datetime
logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.debug('enable crypto API file')
# now_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
# now_date = datetime.datetime.now().strftime('%Y-%m-%d')
# file_prefix = str(os.path.abspath(os.getcwd()))
# folder_name = '\\backup_of_games\\' + now_date
#used on first run
def Main(coins, rowIDs, parameters, headers):
        email_list = []
        con = sq.connect(file_prefix + '\squarewon.db')
        cur = con.cursor()
        sql_insert_bet = 'INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'


        #First extract data from database that was saved when bet button pressed
        players_raw = cur.execute('SELECT * from players')
        players_all_data = players_raw.fetchall()
        #cycle through sql to get each persons crypto VALUES
        Total_list = []
        backup_list = []
        for player in players_all_data:
            coins_dict = {}
            #get the data from each coin, do the math here to get the
            #info needed to make the table
            name = player[0]
            email = player[1]
            bet = player[2:]
            for i, USD_value in enumerate(bet):
                coin_symbol = coins[i]
                symbol_w_USD_bet = {coin_symbol:USD_value}
                coins_dict.update(symbol_w_USD_bet)
            Total_list.append(coins_dict)
            email_list.append(email)
            # backup_list.append({'name':name,'email':email,'bet':coins_dict})
        # print('backup_list',backup_list)
        #Make folder with current date
        # if not os.path.isdir(file_prefix + '\\backup_of_games\\' + now_date):
        #     os.mkdir(file_prefix + '\\backup_of_games\\' + now_date)
        # #backups up initial bet info
        # with open(file_prefix + folder_name + f'\\initial_bet-{now_time}.json', 'w') as json_file:
        #      json.dump({'Player_Bets':backup_list}, json_file)

        #once the data is copied and used here drop the table and redo it
        cur.execute('DROP TABLE players')
        sql_create = 'CREATE TABLE players(name TEXT, email TEXT, {0} FLOAT, {1} FLOAT, {2} FLOAT, {3} FLOAT, {4} FLOAT, {5} FLOAT, {6} FLOAT, {7} FLOAT, {8} FLOAT, {9} FLOAT)'.format(coins[0],coins[1],coins[2],coins[3],coins[4],coins[5],coins[6],coins[7],coins[8],coins[9])
        cur.execute(sql_create)
        con.commit()

        #access API, params and headers passed from flask initial start
        url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        session = Session()
        session.headers.update(headers)
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        #THIS SECTION CREATES THE SQL DATABASE WITH INSERT STATMENT PER PLAYER
        for i, name in enumerate(rowIDs):
            coins_amount = []
            email = email_list[i]
            #cycles through what each player has
            for crypto, usd_bet in Total_list[i].items():
                #converts USD to crypto number
                amount = float(usd_bet/Crypto_to_USD(crypto, data))
                #new_crypto is row headers
                #new amount is just formated amounts with usd value in brackets
                coin_amount = round(amount,4)
                coins_amount.append(coin_amount)
            val = (name, email, coins_amount[0],coins_amount[1],coins_amount[2],coins_amount[3],coins_amount[4],coins_amount[5],coins_amount[6],coins_amount[7],coins_amount[8],coins_amount[9])
            cur.execute(sql_insert_bet, val)
        con.commit()
        con.close()

def updater(coins,rowIDs, parameters, headers, winner):
    con = sq.connect(file_prefix + '\squarewon.db')
    cur = con.cursor()
    # TODO:  make this also gotten from flask
    url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
    session = Session()
    session.headers.update(headers)
    response = session.get(url, params=parameters)
    data = json.loads(response.text)
    #same as main except used previous data
    players_raw = cur.execute('SELECT * from players')
    players_all_data = players_raw.fetchall()
    #cycle through sql to get each persons crypto VALUES
    updated_list = []
    backup_list = []
    for y, player in enumerate(players_all_data):

        updated_dict = {}
        USD_Total_list = []
        #get the data from each coin, do the math here to get the
        #info needed to make the table
        # print(player)
        name = player[0]
        email = player[1]
        bet = player[2:]
        # print(bet)
        for i, coin_value in enumerate(bet):

            coin_symbol = coins[i]
            #new_crypto is row headers
            new_crypto = Nice_header(coin_symbol, data)
            #new amount is just formated amounts with usd value in brackets
            USD_of_coin = float(coin_value*Crypto_to_USD(coin_symbol, data))
            USD_Total_list.append(USD_of_coin)
            new_amount = str(round(coin_value,4)) + '(' + str(round(float(coin_value*Crypto_to_USD(coin_symbol, data)),2)) + ')'
            updated_dict.update({'Total USD':str(round(sum(USD_Total_list),2))})
            updated_dict.update({new_crypto:new_amount})
        #here cycle through the coins from the other program
        backup_list.append({'name':name,'email':email,'Total USD':round(sum(USD_Total_list),2),'bets':updated_dict})
        # updated_list.append(updated_dict)
    def get_total(player):
        return player['Total USD']

    updated_list = sorted(backup_list, key=get_total, reverse=True)
    name_list = []
    for player in updated_list:
        name_list.append(player['name'])

    header = updated_list[0]['bets'].keys()
    rows = [player['bets'].values() for player in updated_list]
    if winner =='no':
        #saves json backups
        # with open(file_prefix + folder_name + f'\\sub_bet-{now_time}.json', 'w') as json_file:
        #      json.dump({'Player_Bets':backup_list}, json_file)
        #updates the same table
        fh = open('templates\HTML_table.html', 'w')
        HTML_table = tabulate(rows, header, tablefmt='html', showindex=name_list)
        fh.write(HTML_table)
        fh.close()
    if winner == 'yes':
        # with open(file_prefix + folder_name + f'\\final_results-{now_time}.json', 'w') as json_file:
        #      json.dump({'Player_Bets':backup_list}, json_file)

        #using final_total search people.values to see who it belogns to
        #get USD amount from above, sort by highest, and link that to the person
        return updated_list[0]

def Crypto_to_USD(crypto, data):
    try:
        logging.debug('Crypto to USD running')
        #data is passed down by Main()
        # TODO: this could be LAMBDA
        return data['data'][crypto][0]['quote']['USD']['price']
    except (ConnectionError, Timeout, TooManyRedirects) as e:
      print(e)

def Nice_header(crypto, data):
    logging.debug('Header running')
    return crypto + '(' + str(round(Crypto_to_USD(crypto, data),3)) + ')'

# TODO: make these classes
