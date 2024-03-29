#!/usr/bin/env python
import telegram
import telegram.ext
import csv
import os
import logging
import pickle
import urllib3
import json
import requests
import time
import datetime
import pandas as pd
from tabulate import tabulate
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from forex_python.converter import CurrencyRates
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import locale

# Set locale time
locale.setlocale( locale.LC_ALL, '' )

CHAT_ID = '-1001183088830'
PROJECT_ID = 'hikari-clientside-py-telegram-bot'
admins = ['helloiamivan']

# File paths to save to (databases)
TELEGRAM_TOKEN = BOT_API
LOCAL_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\'+PROJECT_ID+'\\Output\\OrderBooks\\'
KYC_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\'+PROJECT_ID+'\\KYC\\'

# Import Name/Symbol lookup from Coinmarket Cap snapshot
with open('properties.p', 'rb') as handle:
    name_symbol_dict = pickle.load(handle)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

INIT_REQUEST, BUY_SELL_REQUEST, CRYPTO_REQUEST, \
PRICE_REQUEST, PAYMENT_REQUEST, NATIONALITY_REQUEST, \
PHOTO_REQUEST, REGISTRATION_DONE, CHECK_INPUT, \
ID_NUMBER_REQUEST, SUBMIT, CANCEL_ORDER, \
CHECK_EXPIRY = range(13)

reply_keyboard_submit_details = [
[InlineKeyboardButton("Visit Our Website",url='http://hikari.mobi')],
[InlineKeyboardButton("Create Order",callback_data='Submit Order'),InlineKeyboardButton("Cancel Order",callback_data='Cancel Orders')],
[InlineKeyboardButton("View Orders",callback_data='View Orders'),InlineKeyboardButton("Exit",callback_data='Cancel')]]

reply_keyboard_check_details = [
[InlineKeyboardButton("Confirm Submission",callback_data='Confirm Submission')],
[InlineKeyboardButton("Cancel",callback_data='Cancel')]]

buysell_choice = [
[InlineKeyboardButton("BUY",callback_data='BUY'),InlineKeyboardButton("SELL",callback_data='SELL')]]

crypto_choice = [
[InlineKeyboardButton("BTC/USD",callback_data='BTC')],
[InlineKeyboardButton("ETH/USD",callback_data='ETH')],
[InlineKeyboardButton("ETH/BTC",callback_data='ETHBTC')]]

cancel_order_choice = [InlineKeyboardButton("Go Back",callback_data='Go Back')]

# Keyboard markups here
markup_submit_details = telegram.InlineKeyboardMarkup(reply_keyboard_submit_details)
markup_check_details = telegram.InlineKeyboardMarkup(reply_keyboard_check_details)
buysell_details = telegram.InlineKeyboardMarkup(buysell_choice)
crypto_details = telegram.InlineKeyboardMarkup(crypto_choice)
cancel_order_details = telegram.InlineKeyboardMarkup(cancel_order_choice)

def register_user(username):
    try:
        users = json.load(open('registeredUsers.json'))
        users.append(username)

        with open('registeredUsers.json', 'w+') as fp:
            json.dump(users, fp)
    except:
        users = []
        users.append(username)
        with open('registeredUsers.json', 'w+') as fp:
            json.dump(users, fp)

def check_if_user_registered(username):
    try:
        users = json.load(open('registeredUsers.json'))
        if username in users:
            return True
        else:
            return False
    except:
        return False

def is_positive_number(s):
    try:
        float(s)
        if float(s) > 0:
            return True
        else:
            return False
    except ValueError:
        return False

def getCoinMarketPrice(symbol,fiat_currency):
    # Disable insecure http request warning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    Crypto_name = name_symbol_dict['name'][symbol]

    http = urllib3.PoolManager()
    request = "https://api.coinmarketcap.com/v1/ticker/"+Crypto_name+"/?convert="+fiat_currency
    response = http.request('GET',request)
    cleandata = json.loads(response.data)

    # TODO: Add error catching
    price = str(round(float(cleandata[0]['price_'+fiat_currency.lower()]),4))

    return price

def facts_to_str(user_data):
    facts = list()
    for key, value in user_data.items():
        if key not in ['Current Market Price','Nationality','Full Name','Valid Order ID']:
            facts.append('{} - *{}*'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

def start(bot, update):
    user = update.message.from_user

    # If user don't have a valid telegram handle, end the conversation
    if user.username == None:
        update.message.reply_text("You do not have a valid Telegram username! Please set your Telegram username in your *settings page* before using the bot.",parse_mode=telegram.ParseMode.MARKDOWN)
        return telegram.ext.ConversationHandler.END

    update.message.reply_text(
    "Hello " + user.first_name + "! \n\n"
    "I am here to help you facilitate your order posting. Please fill in some details to post your order in the trading pool.\n"
    " \nType /cancel at any point to exit.",
        reply_markup=markup_submit_details,parse_mode=telegram.ParseMode.MARKDOWN,resize_keyboard=True)

    return INIT_REQUEST

def init_choice(bot, update, user_data):
    query = update.callback_query
    user = update.callback_query.from_user
    choice = query.data

    if choice == 'Cancel':
        reply = ('Bye ' + user.first_name + '! You have successfully exited the bot, press /start to post an order again.')
        bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id)
        return telegram.ext.ConversationHandler.END

    elif choice == 'Submit Order':

        # Check if user is registered with a trading account
        if check_if_user_registered(user.username) == True:

            btc_price = getCoinMarketPrice('BTC','USD')
            eth_price = getCoinMarketPrice('ETH','USD')
            ethbtc_price = getCoinMarketPrice('ETH','BTC')

            reply = ('Do you want to *BUY* or *SELL* cryptocurrencies?\n\n' +
                'Current BTC/USD price is: *' + locale.currency(float(btc_price), grouping=True) + '*\n\n' +
                'Current ETH/USD price is: *' + locale.currency(float(eth_price), grouping=True) + '*\n\n' +
                'Current ETH/BTC price is *' + ethbtc_price + '*\n' +
                '_Source: CoinMarketCap_\n\n'+
                'Press /cancel to abort')
                
            bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,reply_markup=buysell_details,parse_mode=telegram.ParseMode.MARKDOWN)
            return BUY_SELL_REQUEST
        else:
            reply = ('Please register a trading account with us first before you can submit orders into the pool. Thank you!')
            bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,reply_markup=markup_submit_details)
            return INIT_REQUEST

    elif choice == 'Register':

        if check_if_user_registered(user.username) == True:
            reply = ('You have already registered an account.')
            bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,reply_markup=markup_submit_details)

            return INIT_REQUEST
        else:
            reply = ('For KYC (Know your customer) purposes, please enter your full name to begin registering an account with us.')
            bot.sendMessage(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id)  
            
            return NATIONALITY_REQUEST

    elif (choice == 'View Orders') | (choice == 'Cancel Orders'):

        # Read data to order book
        orderbook_eth = pd.read_csv(LOCAL_FILE_PATH + 'ETH.csv',header=None)
        orderbook_btc = pd.read_csv(LOCAL_FILE_PATH + 'BTC.csv',header=None)
        orderbook_ethbtc = pd.read_csv(LOCAL_FILE_PATH + 'ETHBTC.csv',header=None)
        orderbook = pd.concat([orderbook_eth,orderbook_btc,orderbook_ethbtc],ignore_index=True)

        orderbook.columns = ['OrderID','Side','User','Coin','Quantity','Price','Fiat','Time','Epoch_Time','Status']
        orderbook.loc[orderbook['Coin'] == 'ETHBTC','Price'] = 'B' + orderbook['Price'].astype(str)
        orderbook.loc[orderbook['Coin'] != 'ETHBTC','Price'] = '$' + orderbook['Price'].astype(str)
        orderbook = orderbook.ix[(orderbook['User'] == user.username)].copy()
        orders = orderbook.ix[(orderbook['Status'] == 'OPEN')].copy()
        orders.sort_values(by=['Epoch_Time'],inplace=True)

        # If there are no orders
        if orders.empty:
            reply = ('You have not posted any orders yet. Click submit order to post your order into the pool.')
            bot.sendMessage(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,reply_markup=markup_submit_details)
            return INIT_REQUEST

        else:
            orders = orders[['OrderID','Side','Coin', 'Quantity', 'Price','Time']].copy()
            # Descending time
            orders = orders.iloc[::-1].copy()
            prettyprint_orders = tabulate(orders,tablefmt='simple',headers='keys',showindex=False,stralign='left',numalign='left')
            
            if choice == 'View Orders':
                reply = ('Here are your orders:\n\nNote that all times are in UTC\n\n' + prettyprint_orders)
                bot.sendMessage(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,reply_markup=markup_submit_details)
                return INIT_REQUEST

            if choice == 'Cancel Orders':
                reply = ('Please enter the order ID of the order you wish to cancel below. Note that all times are in UTC Press /cancel to abort!:\n\n' + prettyprint_orders)
                bot.sendMessage(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id)
                user_data['Valid Order ID'] = orders.OrderID.tolist()
                return CANCEL_ORDER

    else:
        pass

def nationality_request(bot,update,user_data):
    text = update.message.text
    user_data['Name'] = text

    reply = ('Please enter your nationality.')

    bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id)

    return ID_NUMBER_REQUEST

def id_number_request(bot,update,user_data):
    text = update.message.text
    user_data['Nationality'] = text

    reply = ('Please enter your passport identification number.')

    bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id)

    return PHOTO_REQUEST

def photo_request(bot,update,user_data):
    text = update.message.text
    user_data['ID Number'] = text

    reply = ('Please send us a photo of the front page of your passport.')

    bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id)
    
    return REGISTRATION_DONE

def registration_done(bot,update,user_data):
    user = update.message.from_user

    if update.message.photo == None:
        reply = ('Please try sending us a photo of your passport again, contact our admins if you have any difficulty.')
        bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id)
        
        return REGISTRATION_DONE
    else:
        # Download the photo
        picture = bot.getFile(update.message.photo[3]['file_id'])
        photo_path = KYC_FILE_PATH + user.username + '.jpg'
        picture.download(photo_path)

        # Save all the details
        fields = ['','','','','','']

        fields[0] = user.username
        fields[1] = user_data['Name']
        fields[2] = user_data['Nationality']
        fields[3] = user_data['ID Number']
        fields[4] = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        fields[5] = 'UNCONFIRMED'

        # Save data to order book
        file = open(KYC_FILE_PATH + 'Users.csv','a+',newline='')
        writer = csv.writer(file)
        writer.writerow(fields)
        file.close()

        reply = ('Thank you for submitting your details! Your account will be reviewed by our team before you can start trading.')

        bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id,reply_markup=markup_submit_details)

        return INIT_REQUEST

def cancel_order(bot,update,user_data):
    order_id = update.message.text
    user = update.message.from_user

    if order_id in user_data['Valid Order ID']:
        if len(order_id) == 6:
            crypto = order_id[0] + order_id[1]
        else:
            crypto = order_id[0]

        if crypto == 'B':
            cryptoFile = 'BTC'
        elif crypto == 'E':
            cryptoFile = 'ETH'
        elif crypto == 'EB':
            cryptoFile = 'ETHBTC'           
        else:
            raise('Unknown file to open when cancelling order!')

        orderbook = pd.read_csv(LOCAL_FILE_PATH + cryptoFile + '.csv',header=None)
        orderbook = orderbook.set_index(0)
        orderbook.columns = ['Side','User','Coin','Quantity','Local_Price','Expiry','Time','Epoch_Time','Status']
        orderbook.ix[order_id,'Status'] = 'CANCELLED'
        orderbook.to_csv(LOCAL_FILE_PATH + cryptoFile + '.csv',header=False)

        reply = ('Your order ' + order_id + ' has been successfully cancelled. You can now continue to submit another order or view your existing orders.')

        # Reply this to user
        bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id,reply_markup=markup_submit_details)

        # Send message to private pool
        bot.sendMessage(chat_id=CHAT_ID,text=('@'+user.username.replace('_','\\_') + ' cancelled an order!'+ '\n' 
                + 'Order ID: ' + order_id + '\n'),parse_mode=telegram.ParseMode.MARKDOWN)
        
        del user_data['Valid Order ID']

        return INIT_REQUEST
    else:
        reply = ('The Order ID is invalid, please note that the order id is case sensitive. Try again below. Press /cancel to exit.')
        bot.sendMessage(text=reply,chat_id=update.message.chat_id,message_id=update.message.message_id)
        return CANCEL_ORDER

def buy_sell_choice(bot, update, user_data):
    query = update.callback_query
    user = update.callback_query.from_user
    choice = query.data

    user_data['Order'] = choice

    reply = ('Please choose to *' + choice + '* the following pairs available below.')
    bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=crypto_details) 
    return CRYPTO_REQUEST

def crypto_choice(bot, update, user_data):
    query = update.callback_query
    user = update.callback_query.from_user
    choice = query.data

    user_data['Cryptocurrency'] = choice

    reply = ('Please input the amount of ' + choice 
        + ' you wish to buy/sell below.\n\nNote that quantities will be rounded to 4 decimal places\n\n')

    bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id)

    return PRICE_REQUEST

def price_choice(bot,update,user_data):
    choice = update.message.text.lower()

    if is_positive_number(choice) == True:
        user_data['Quantity'] = str(round(float(choice),4))

        if user_data['Cryptocurrency'] == 'ETHBTC':
            coin_price = getCoinMarketPrice('ETH','BTC')
        else:
            coin_price = locale.currency(float(getCoinMarketPrice(user_data['Cryptocurrency'],'USD')), grouping=True)

        reply = ('What price would you like to set your order at?\n\nPlease enter "m" for market orders or only numbers for prices, note that your price will be rounded to 4 decimal places.\n\n'
                'Current ' + user_data['Cryptocurrency'] + ' price is: ' + coin_price + '\n' +
                'Source: CoinMarketCap\n\n')
       
        update.message.reply_text(reply)
        return CHECK_EXPIRY

    else:
        reply = 'Sorry, please only enter a positive number for quantity. Try again or type /cancel to exit.'
        update.message.reply_text(reply)
        return PRICE_REQUEST

def check_expiry(bot,update,user_data):
    choice = update.message.text.lower()

    # Check if price is a number
    if is_positive_number(choice)==False and choice != 'm' :
        update.message.reply_text('Price must be a positive number! For market orders, please enter "M". Please enter the price again or type /cancel to exit')
        return CHECK_EXPIRY
    else:
        # Get the price as a string
        if choice == 'm':
            user_data['Price'] = 'Market'
            user_data['Total Order Amount'] = 'Market'         
            user_data['Price'] = choice    

        else:
            user_data['Price'] = str(round(float(choice),4))
            if user_data['Cryptocurrency'] == 'ETHBTC':
                user_data['Total Order Amount'] = str(round(float(user_data['Price']) * float(user_data['Quantity']),4)) + " BTC"
            else:
                user_data['Total Order Amount'] = locale.currency(round(float(user_data['Price']) * float(user_data['Quantity']),0), grouping=True)          

        reply = ("Please let us know when would you like your order to expire.\n\nWe support expiries from a minimum of 1 hour and up to a maximum of 30 days.\n\n"
            "For example, please type '3h' for an order expiry of 3 hours, and '10d' for an expiry of 10 days. Type 'GTC' if you wish for your order to be good till cancelled.\n\n"
            "Note that the expiry timer will only start when your order is submitted successfully.")

        update.message.reply_text(reply,parse_mode=telegram.ParseMode.MARKDOWN)

        return CHECK_INPUT

def check_input(bot, update, user_data):
    choice = update.message.text.lower()

    # Get the price as a string
    user_data['Expiry'] = choice

    # Add disclaimer
    disclaimer = ("By pressing Confirm Submission, you accept our terms and conditions for using our OTC trading pool." + 
        " Hit Cancel now if you do not accept the terms.")

    reply = ("Please check the following details carefully before submitting your order:" + "\n" 
        + "{}".format(facts_to_str(user_data)) + "\n" + disclaimer)

    update.message.reply_text(reply,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=markup_check_details)
    
    return SUBMIT

def done(bot, update, user_data):
    query = update.callback_query
    user = update.callback_query.from_user
    selection = query.data

    if selection == 'Cancel':
        reply = ("Your details are not submitted. Type /start again to restart the submission")
        bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id)

        return telegram.ext.ConversationHandler.END

    elif selection == 'Confirm Submission':
        
        fields = ['','','','','','','','','','']

        try:
            orderbook = pd.read_csv(LOCAL_FILE_PATH + '\\'+user_data['Cryptocurrency']+'.csv',header=None)
            ordercount = len(orderbook.index)
        except:
            ordercount = 0
        
        if user_data['Cryptocurrency'] == 'ETHBTC':
            orderID = 'EB'+ "%04d" % (ordercount,)
        else:
            orderID = user_data['Cryptocurrency'][0] + "%04d" % (ordercount,)

        # Fill in the list of information
        fields[0] = orderID
        fields[1] = user_data['Order']
        fields[2] = user.username
        fields[3] = user_data['Cryptocurrency']
        fields[4] = user_data['Quantity']
        fields[5] = user_data['Price']
        fields[6] = user_data['Expiry']
        fields[7] = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        fields[8] = time.time()
        fields[9] = 'OPEN'

        if user_data['Price'] == 'Market':
            price_string = 'Market*'
        else:
            if user_data['Cryptocurrency'] == 'ETHBTC':
                price_string = user_data['Price'] + ' BTC each*'
            else:
                price_string = user_data['Price'] + ' USD each*'

        # If valid telegram handle
        if (fields[1] != None):
            bot.sendMessage(chat_id=CHAT_ID,text=('*[' + user_data['Order'] 
                + '] ' + user_data['Quantity'] + ' ' + user_data['Cryptocurrency'] + ' @ ' 
                + price_string + '\n' 
                + 'Total: ' + user_data['Total Order Amount'] + '\n'
                + 'Expiry: ' + user_data['Expiry'] + '\n'
                + 'Contact @' + user.username.replace('_','\\_') + '\n' 
                + 'Order ID: ' + orderID + '\n'
                + "Posted on _" + datetime.date.today().strftime("%B %d, %Y") + '_'),parse_mode=telegram.ParseMode.MARKDOWN)

            # Save data to order book
            file = open(LOCAL_FILE_PATH + user_data['Cryptocurrency']+'.csv','a+',newline='')
            writer = csv.writer(file)
            writer.writerow(fields)
            file.close()

            reply = "Thank you for submitting your order details, one of our admins will contact you shortly if there is a match. You can now post another order, cancel an order or choose to view your existing orders.\n\nYour order is as follows:\n" + "{}".format(facts_to_str(user_data))

            bot.editMessageText(text=reply,chat_id=query.message.chat_id,message_id=query.message.message_id,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=markup_submit_details)

            logger.info(user.username + ' has successfully posted an order!')
        
        user_data.clear()

        return INIT_REQUEST

    else:
        pass

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def cancel(bot, update):
    user = update.message.from_user
    update.message.reply_text('Bye ' + user.first_name + '! You have successfully exited from the bot. Press /start to post an order again.')

    return telegram.ext.ConversationHandler.END

def register(bot,update):
    text = update.message.text
    user = update.message.from_user.username

    if user in admins:
        if text.find('@') != -1:
            new_user = text[text.find('@')+1::]
            if check_if_user_registered(new_user) == False:
                register_user(new_user)
                update.message.reply_text('Successfully added new account for ' + new_user)
            else:
                update.message.reply_text(new_user + ' already has a trading account!')
    else:
        update.message.reply_text('Only admins can access this function')
    
    return telegram.ext.ConversationHandler.END

def delete(bot,update):
    text = update.message.text
    user = update.message.from_user.username

    if user in admins:
        if text.find('@') != -1:
            new_user = text[text.find('@')+1::]
            registered_users = json.load(open('registeredUsers.json'))

            if new_user in registered_users:
                registered_users.remove(new_user)

                with open('registeredUsers.json', 'w+') as fp:
                    json.dump(registered_users, fp)

                update.message.reply_text('Successfully deleted account for ' + new_user)
            else:
                update.message.reply_text(new_user + ' already has a trading account!')
    else:
        update.message.reply_text('Only admins can access this function')
    
    return telegram.ext.ConversationHandler.END

def main():
    # Create the Updater and pass it your bot's token.
    updater = telegram.ext.Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler
    conv_handler = telegram.ext.ConversationHandler(
        entry_points=[telegram.ext.CommandHandler('start', start)],

        states={
            INIT_REQUEST: [telegram.ext.CallbackQueryHandler(init_choice,
                                    pass_user_data=True),
                       ],

            NATIONALITY_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    nationality_request,
                                    pass_user_data=True),
                       ],

            ID_NUMBER_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    id_number_request,
                                    pass_user_data=True),
                       ],

            PHOTO_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    photo_request,
                                    pass_user_data=True),
                       ],

            REGISTRATION_DONE: [telegram.ext.MessageHandler((telegram.ext.Filters.photo|telegram.ext.Filters.text),
                                    registration_done,
                                    pass_user_data=True),
                       ],      

            BUY_SELL_REQUEST: [telegram.ext.CallbackQueryHandler(buy_sell_choice,
                                    pass_user_data=True),
                       ],

            CRYPTO_REQUEST: [telegram.ext.CallbackQueryHandler(crypto_choice,
                                    pass_user_data=True),
                       ],

            PRICE_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    price_choice,
                                    pass_user_data=True),
                       ],

            CANCEL_ORDER: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    cancel_order,
                                    pass_user_data=True),
                       ],

            CHECK_EXPIRY:[telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    check_expiry,
                                    pass_user_data=True)
                       ],

            CHECK_INPUT:[telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    check_input,
                                    pass_user_data=True)
                       ],

            SUBMIT: [telegram.ext.CallbackQueryHandler(done,
                                    pass_user_data=True)
                       ],                                
        },

        fallbacks=[telegram.ext.CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # Command handlers
    dp.add_handler(telegram.ext.CommandHandler('start', start))
    dp.add_handler(telegram.ext.CommandHandler('cancel', cancel))
    dp.add_handler(telegram.ext.CommandHandler('register', register))
    dp.add_handler(telegram.ext.CommandHandler('delete', delete))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    print("Bot is running... Press Ctrl + C to end it")
    main()
