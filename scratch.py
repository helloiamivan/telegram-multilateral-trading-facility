import pickle
import numpy as np
import pandas as pd
from tabulate import tabulate

# Read data to order book
orderbook_eth = pd.read_csv('Output/OrderBooks/ETH.csv',header=None)
orderbook_btc = pd.read_csv('Output/OrderBooks/BTC.csv',header=None)
orderbook_ethbtc = pd.read_csv('Output/OrderBooks/ETHBTC.csv',header=None)
orderbook = pd.concat([orderbook_eth,orderbook_btc,orderbook_ethbtc],ignore_index=True)

orderbook.columns = ['OrderID','Side','User','Coin','Quantity','Price','Fiat','Time','Epoch_Time','Status']
orderbook.loc[orderbook['Coin'] == 'ETHBTC','Price'] = '₿' + orderbook['Price'].astype(str)
orderbook.loc[orderbook['Coin'] != 'ETHBTC','Price'] = '$' + orderbook['Price'].astype(str)
orderbook = orderbook.ix[(orderbook['User'] == 'helloiamivan')].copy()
orders = orderbook.ix[(orderbook['Status'] == 'OPEN')].copy()
orders.sort_values(by=['Epoch_Time'],inplace=True)
orders = orders[['OrderID','Side','Coin', 'Quantity', 'Price','Time']].copy()
# Descending time
orders = orders.iloc[::-1].copy()
prettyprint_orders = tabulate(orders,tablefmt='simple',headers='keys',showindex=False,stralign='left',numalign='left')
print(prettyprint_orders)
