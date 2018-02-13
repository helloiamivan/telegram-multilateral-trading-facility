#!/usr/bin/env python
import telegram
import telegram.ext
import csv
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

# Set debug = False for PROD
debug = False
admins = ['dotdotc']
CHAT_ID = "@CryptoMYs"
PROJECT_ID = 'cryptomy'
GOOGLE_MAP_API_KEY = "AIzaSyBL40CapX5bhQ7HTQeQkko0oTf59bZQj7A"
convertor = CurrencyRates()

# Define max post count every 24 rolling hours
max_post_count_per_day = 10

# File paths to save to (databases)
if debug == False:
    # @fiddling_bot
    TELEGRAM_TOKEN = "521104355:AAFnA8HHG-fA8X9_Ss8YPfXP9ho3UVXVjEI"
    LOCAL_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\Python\\otc-telegram-bot\\'+PROJECT_ID+'\\Output\\OrderBooks\\'
    REP_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\Python\\otc-telegram-bot\\'+PROJECT_ID+'\\Output\\Reputation.csv'
    COUNT_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\Python\\otc-telegram-bot\\'+PROJECT_ID+'\\Output\\UserPostCount.csv'
    MARKET_DATA_FILE_PATH = 'C:\\Users\\Administrator\\Dropbox\\Python\\crypto-portfolio-telegram\\marketdata\\currentprices.csv'
else:
    # @testtakerbot
    TELEGRAM_TOKEN = "490230105:AAE-qtQ3Db8fyx_i3McE9_hiezQAE3hKl1E"
    LOCAL_FILE_PATH = '/Users/ivanchan/Dropbox/Python/otc-telegram-bot/'+PROJECT_ID+'/Output/OrderBooks/'
    REP_FILE_PATH = '/Users/ivanchan/Dropbox/Python/otc-telegram-bot/'+PROJECT_ID+'/Output/Reputation.csv'
    COUNT_FILE_PATH = '/Users/ivanchan/Dropbox/Python/otc-telegram-bot/'+PROJECT_ID+'/Output/UserPostCount.csv'
    MARKET_DATA_FILE_PATH = '/Users/ivanchan/Dropbox/Python/crypto-portfolio-telegram/marketdata/currentprices.csv'

# Import Name/Symbol lookup from Coinmarket Cap snapshot
with open('properties.p', 'rb') as handle:
    name_symbol_dict = pickle.load(handle)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

INIT_REQUEST, BUY_SELL_REQUEST, CRYPTO_REQUEST, \
FIAT_REQUEST, PRICE_REQUEST, PAYMENT_REQUEST, \
LOCATION_REQUEST, WRONG_INPUT,UPDATE_CUSTOM_LOCATION, \
EXISTING_ORDER_REQUEST, CHECK_INPUT, SUBMIT = range(12)

# Define keyboards here
reply_keyboard_submit_details = [['Submit Order'],['View Existing Orders'],['Cancel']]
reply_keyboard_check_details = [['Confirm Submission'],['Go Back']]
fiat_choice = [['USD','GBP','EUR'],['HKD','SGD','MYR'],['CNY','KRW','JPY']]
buysell_choice = [['BUY'],['SELL']]
payment_choice = [['Paypal / Bank Transfer ONLY'],['Cash on meetup ONLY'], ['Escrow ONLY'], ['Any transaction method'] ]

# Location keyboard here
location_button = telegram.KeyboardButton(text="Send current location",  request_location=True)
location_keyboard = [[location_button],['Enter my own location'],['I do not wish to share my location']]

# Keyboard markups here
location_details = telegram.ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True)
markup_submit_details = telegram.ReplyKeyboardMarkup(reply_keyboard_submit_details,one_time_keyboard=True)
markup_check_details = telegram.ReplyKeyboardMarkup(reply_keyboard_check_details,one_time_keyboard=True)
buysell_details = telegram.ReplyKeyboardMarkup(buysell_choice, one_time_keyboard=True)
fiat_details = telegram.ReplyKeyboardMarkup(fiat_choice, one_time_keyboard=True)
payment_details = telegram.ReplyKeyboardMarkup(payment_choice, one_time_keyboard=True)
current_price_details = telegram.ReplyKeyboardMarkup([['Use Current Price']], one_time_keyboard=True)

# TODO refactor into a function flattening lists
valid_fiat = [item for sublist in fiat_choice for item in sublist]

def rank_rep(rep):

    if rep <= 10.0:
        return "Plankton👾"

    elif 10.0 < rep <= 30.0:
        return "Fish🐟"

    elif 30.0 < rep <= 50.0:
        return "Dolphin🐬"

    elif 50.0 < rep <= 100.0:
        return "Shark🦈"

    elif rep > 100.0:
        return "Whale🐳"

    else:
        return "Unknown"

def is_valid_coin(s):
    marketdata = pd.read_csv(MARKET_DATA_FILE_PATH)
    coin = marketdata.ix[marketdata['symbol']==s]
    if coin.empty:
        return False
    else:
        return True

def is_positive_number(s):
    try:
        float(s)
        if float(s) > 0:
            return True
        else:
            return False
    except ValueError:
        return False

# TODO: fix bug when location API doesn't work
def get_location(lat,lon):
    validLocation = False
    retries = 0

    # Use google map geo api
    url = "http://maps.googleapis.com/maps/api/geocode/json?"
    url += "&latlng=%s,%s&api=" % (lat, lon)
    url += GOOGLE_MAP_API_KEY
    http = urllib3.PoolManager()

    while (validLocation == False) and (retries <= 3):
        response = http.request('GET', url)
        data = json.loads(response.data.decode('utf-8'))

        if len(data['results']) < 1:
            time.sleep(1.0)
            retries += 1
        else:
            validLocation = True
            logger.info('Location obtained after %s attempts' % retries)
    
    # Initialize none for area and country
    country = area = None

    if (retries >= 3) and (validLocation == False):
        return area,country
    else:
        components = data['results'][0]['address_components']      
        # Get area and country
        for c in components:
            if "country" in c['types']:
                country = c['long_name']
            if "administrative_area_level_1" in c['types']:
                area = c['long_name']
        return area,country

def getCoinMarketPrice(symbol,fiat_currency):
    # Disable insecure http request warning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    Crypto_name = name_symbol_dict['name'][symbol]

    http = urllib3.PoolManager()

    if fiat_currency == 'MYR':
        request = "https://api.coinmarketcap.com/v1/ticker/"+Crypto_name+"/?convert=USD"
        response = http.request('GET',request)
        cleandata = json.loads(response.data)
        price = str(round(float(cleandata[0]['price_usd']) * convertor.get_rate('USD',fiat_currency),4))
    else:
        request = "https://api.coinmarketcap.com/v1/ticker/"+Crypto_name+"/?convert="+fiat_currency
        response = http.request('GET',request)
        cleandata = json.loads(response.data)
        # TODO: add error catching
        price = str(round(float(cleandata[0]['price_'+fiat_currency.lower()]),4))
    
    return price

def facts_to_str(user_data):
    facts = list()
    for key, value in user_data.items():
        if key != 'Current Market Price':
            facts.append('{} - *{}*'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

def post_count(username,filename):
    postcountData = pd.read_csv(filename,header=None)
    timeCondition = time.time() - (24*60*60)
    postcountData.columns = ['User','Time']
    maxusage = postcountData.ix[(postcountData['Time']>timeCondition) & (postcountData['User']==username)].copy()
    return(len(maxusage.index))

def rep_count(username,filename):
    repcountData = pd.read_csv(filename,header=None)
    repcountData.columns = ['User','Voted User','Rep Vote','Time']
    repcount = repcountData.ix[(repcountData['Voted User']==username)].copy()
    if repcount.empty:
        repcountnumber = 0
    else:
        repcountnumber = repcount['Rep Vote'].sum()
    return repcountnumber

def check_rep_post(username,filename,adminlist):
    if username in adminlist:
        return int(0)
    else:
        repcountData = pd.read_csv(filename,header=None)
        repcountData.columns = ['User','Voted User','Rep Vote','Time']
        timeCondition = time.time() - (24*60*60)
        repcount = repcountData.ix[(repcountData['User']==username) & (repcountData['Time'] > timeCondition)].copy()
        return (len(repcount.index))

def start(bot, update):
    user = update.message.from_user
    # If user don't have a valid telegram handle, end the conversation
    if user.username == None:
        update.message.reply_text("You do not have a valid Telegram username! Please set your Telegram username in your *settings page* before submitting your details.",parse_mode=telegram.ParseMode.MARKDOWN)
        return telegram.ext.ConversationHandler.END

    post_count_instances = post_count(user.username,COUNT_FILE_PATH)

    update.message.reply_text(
    "Hello " + user.first_name + "! "
    "Cryptocurrency Mart is a *free to use* channel where users can post their interest in exchanging fiat and cryptocurrencies with other users at *ZERO exchange fees*.\n"
    " \n"
    "I am here to help you facilitate your order posting. Please fill in some details to post on the Cryptocurrency Mart Channel.\n"
    " \n"
    "*You currently have " + str(post_count_instances) + " post counts in the last 24 hours.*"
    "To prevent spam, users are limited to a maximum of " + str(max_post_count_per_day) + " posts (buy/sell) every 24 hours. Type /cancel at any point to exit.",
        reply_markup=markup_submit_details,parse_mode=telegram.ParseMode.MARKDOWN,resize_keyboard=True)
    #update.message.reply_text("*** [27 Dec 2017] Introducing the reputation system! Type /rep to find out a user's reputation, type /upvote or /downvote to vote a user!***")
    
    return INIT_REQUEST

def init_choice(bot, update, user_data):
    choice = update.message.text
    user = update.message.from_user
    # Get the post counts user has posted in last 24 hours
    post_count_instances = post_count(user.username,COUNT_FILE_PATH)

    if choice == 'Cancel':
        update.message.reply_text('Bye ' + user.first_name + '! Your order is not posted. I hope you would use Cryptocurrency Mart again someday!')
        return telegram.ext.ConversationHandler.END

    elif choice == 'Submit Order':
        # Check post count max
        if post_count_instances >= max_post_count_per_day:
            update.message.reply_text("You have exceeded your maximum posts in the last 24 hours!")
            return telegram.ext.ConversationHandler.END
        else:
            update.message.reply_text('Do you want to BUY or SELL cryptocurrencies?',reply_markup=buysell_details)
            return BUY_SELL_REQUEST

    elif choice == 'View Existing Orders':
        # Check existing orders
        update.message.reply_text('Which cryptocurrency you would like to view existing orders in the last 48 hrs?\n\n' + 
            'Type in the ticker of the coin you wish to view. For example, *type BTC for Bitcoin*. We currently only support coins listed on CoinMarketCap.com.' +
             'Type /cancel to exit.',parse_mode=telegram.ParseMode.MARKDOWN)
        return EXISTING_ORDER_REQUEST

    else:
        return wrong_input(update)

def existing_order_choice(bot,update,user_data):
    text = update.message.text.upper()
    if is_valid_coin(text):
        try:
            # Read data to order book
            orderbook = pd.read_csv(LOCAL_FILE_PATH + text+'.csv',header=None)
            timeCondition = time.time() - (48*60*60)
            orderbook.columns = ['Side','User','Coin','Quantity','Local_Price','Fiat','Time']
            orderbook['Price'] = orderbook['Local_Price'].astype(str) + ' ' + orderbook['Fiat'].astype(str)
            orders = orderbook.ix[(orderbook['Time']>timeCondition)].copy()
            # If there are no orders
            if orders.empty:
                update.message.reply_text('There are no orders for ' + text + ' in the last 48 hours!\n\nHow about posting one by pressing /start?')
            else:
                orders = orders[['Side','User','Quantity', 'Price']].copy()
                # Descending time
                orders = orders.iloc[::-1].copy()
                orders['User'] = '@' + orders['User'].astype(str)
                prettyprint_orders = tabulate(orders,tablefmt='plain',headers='keys',showindex=False,stralign='center',numalign='center')
                update.message.reply_text(text + ' orderbook in the last 48 hours:\n\n' + 'Note that orders are listed from new to old. Press /start to start posting!\n\n'  + prettyprint_orders)
        
        except:
            update.message.reply_text('There are no orders for ' + text + ' in the last 48 hours!\n\nHow about posting one by pressing /start?')
    else:
        update.message.reply_text('Invalid ticker! Please only choose from coins listed on CoinMarketCap.com! Type in your coin ticker again or type /cancel to exit')
        return EXISTING_ORDER_REQUEST

    return telegram.ext.ConversationHandler.END

def buy_sell_choice(bot, update, user_data):
    text = update.message.text.upper()
    if (text != 'BUY') and (text != 'SELL'):
        update.message.reply_text("Please only input BUY or SELL!",reply_markup=buysell_details)
        return BUY_SELL_REQUEST
    else:
        user_data['Order'] = text
        update.message.reply_text('Please type below the ticker of the coin you wish to ' + text +
            '.\n\n*For example, type BTC for Bitcoin.* We currently only support coins listed on CoinMarketCap.com. Type /cancel to exit.',parse_mode=telegram.ParseMode.MARKDOWN) 
        return CRYPTO_REQUEST

def crypto_choice(bot, update, user_data):
    text = update.message.text.upper()
    if is_valid_coin(text):
        user_data['Cryptocurrency'] = text
        update.message.reply_text(
            'Please input the amount of ' + text + ' you wish to buy/sell below. (Quantities will be rounded to 4 decimal places)')
        return FIAT_REQUEST
    else:
        update.message.reply_text('Invalid ticker! Please only choose from coins listed on CoinMarketCap.com! Type in your coin ticker again or type /cancel to exit')
        return CRYPTO_REQUEST

def fiat_choice(bot,update,user_data):
    text = update.message.text

    if is_positive_number(text):
        user_data['Quantity'] = str(round(float(text),4))
        update.message.reply_text('Which fiat currency would you like to transact in?', reply_markup=fiat_details)
        return PRICE_REQUEST
    else:
        update.message.reply_text('Quantity must be a number! Please enter the quantity again or type /cancel to exit')
        return FIAT_REQUEST

def price_choice(bot,update,user_data):
    text = update.message.text

    if (text in valid_fiat):
        user_data['Fiat Currency'] = text
        user_data['Current Market Price'] = getCoinMarketPrice(user_data['Cryptocurrency'],user_data['Fiat Currency'])
        update.message.reply_text('What price would you like to set your order at? Current ' 
        + user_data['Cryptocurrency'] + ' price is: *' + user_data['Current Market Price'] + ' ' + user_data['Fiat Currency']
        +'*'+'. You can enter your own price or choose to use the current price' ,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=current_price_details)
        return PAYMENT_REQUEST

    else:
        update.message.reply_text('Please only choose from the supported fiat currencies below! Try again or type /cancel to exit', reply_markup=fiat_details)
        return PRICE_REQUEST

def payment_choice(bot,update,user_data):
    text = update.message.text

    # Check if price is a number
    if is_positive_number(text)==False:
        if text == 'Use Current Price':
            user_data['Price'] = user_data['Current Market Price']
        else:
            update.message.reply_text('Price must be a positive number! Please enter the price again or type /cancel to exit')
            return PAYMENT_REQUEST
    else:
        # Get the price as a string
        user_data['Price'] = str(round(float(text),4))

    # Compute total order amount
    user_data['Total Order Amount'] = str(round(float(user_data['Price']) * float(user_data['Quantity']),2)) + " " + user_data['Fiat Currency']

    # Now request for location
    update.message.reply_text('Please enter your preferred transaction method.',reply_markup=payment_details)
    return LOCATION_REQUEST

def location_choice(bot,update,user_data):
    # TODO: Error checking for payment method
    text = update.message.text
    user_data['Payment Method'] = text

    # Request user for location
    update.message.reply_text('Please share your location to faciliate matching orders. Press /cancel to exit.', reply_markup=location_details)
    return CHECK_INPUT

def check_input(bot, update, user_data):
    text = update.message.text

    if text == 'I do not wish to share my location':
        user_data['Location'] = 'Undisclosed Location'

    elif text == 'Enter my own location':
        update.message.reply_text('Please enter your location in this format: "City, Country":')
        return UPDATE_CUSTOM_LOCATION

    # If we actually get a location geo coordinate
    elif update.message.location != None:
        location = update.message.location
        [area,country] = get_location(location['latitude'],location['longitude'])

        if area != None:
            user_data['Location'] = str(area) + ',' + str(country)

        elif (area == None) & (country == None):
            update.message.reply_text('Sorry, location services for your device seems to be not working now, please manually enter your location in this format: "City,Country"')
            return UPDATE_CUSTOM_LOCATION

        else:
            user_data['Location'] = str(country)
    else:
        update.message.reply_text('Sorry, I do not recognise that input, type /start to begin again or /cancel to exit.!')
        return telegram.ext.ConversationHandler.END

    disclaimer = ("By pressing Confirm Submission, you accept our terms and conditions " +
    "for using Cryptocurrency Market." + 
    " We are *NOT responsible* for any loss of fiat or cryptocurrencies." +
    " Hit Go Back now if you do not accept the terms.")

    update.message.reply_text("Please check the following details carefully before submitting your order:" + "\n" +
                            "{}".format(facts_to_str(user_data)) + "\n" + disclaimer,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=markup_check_details,resize_keyboard=True)
    return SUBMIT

def check_input_location(bot,update,user_data):
    text = update.message.text

    user_data['Location'] = text

    disclaimer = ("By pressing Confirm Submission, you accept our terms and conditions " +
    "for using Cryptocurrency Market." + 
    " We are *NOT responsible* for any loss of fiat or cryptocurrencies." +
    " Hit *Go Back* now if you do not accept the terms.")

    update.message.reply_text("Please check the following details carefully before submitting your order:" + "\n" +
                            "{}".format(facts_to_str(user_data)) + "\n" + disclaimer,parse_mode=telegram.ParseMode.MARKDOWN,reply_markup=markup_check_details,resize_keyboard=True)
    return SUBMIT

def done(bot, update, user_data):
    selection = update.message.text

    if selection == 'Go Back':
        update.message.reply_text("Your details are not submitted. Type /start again to restart the submission")
        return telegram.ext.ConversationHandler.END

    elif selection == 'Confirm Submission':
        fields = ['','','','','','','']

        # Grab telegram handle
        user = update.message.from_user

        # Fill in the list of information
        fields[0] = user_data['Order']
        fields[1] = user.username
        fields[2] = user_data['Cryptocurrency']
        fields[3] = user_data['Quantity']
        fields[4] = user_data['Price']
        fields[5] = user_data['Fiat Currency']
        fields[6] = time.time()

        # If valid telegram handle
        if (fields[1] != None):

            # Check reputation rank
            reputation_number = rep_count(voted_user,REP_FILE_PATH)
            rep_rank = rep_rank(reputation_number)

            bot.sendMessage(chat_id=CHAT_ID,text=('*[' + user_data['Order'] 
                + '] ' + user_data['Quantity'] + ' ' + user_data['Cryptocurrency'] + ' @ ' 
                + user_data['Price'] + ' ' + user_data['Fiat Currency']+ ' each*'  + '\n' 
                + 'Total: '+ user_data['Total Order Amount'] + '\n' + 'Contact @' + user.username.replace('_','\\_')
                + '\n' + 'User reputation: ' + str(reputation_number) + ' [' + rep_rank + ']'
                + '\n' + user_data['Location'] + "\n" + user_data['Payment Method'] + '\n'
                + "Posted on _" + datetime.date.today().strftime("%B %d, %Y") + '_'),parse_mode=telegram.ParseMode.MARKDOWN)

            # Save data to order book
            file = open(LOCAL_FILE_PATH+user_data['Cryptocurrency']+'.csv','a+',newline='')
            writer = csv.writer(file)
            writer.writerow(fields)
            file.close()

            # Save user count
            countFields = [user.username,time.time()]
            file = open(COUNT_FILE_PATH,'a+',newline='')
            writer = csv.writer(file)
            writer.writerow(countFields)
            file.close()

            update.message.reply_text("Thank you for submitting your order posting, your posting should appear on the channel @cryptocurrencymart shortly. " +
                'Please be careful when transacting online, always check the reputation of a user by typing /rep as a precaution. '+ 
                'We recommend using a trusted broker for a smooth transaction, especially for very large orders. Type /escrow to learn more!')

            logger.info(user.username + ' has successfully posted an order!')
        
        user_data.clear()

        return telegram.ext.ConversationHandler.END

    else:
        return wrong_input(update)

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def cancel(bot, update):
    user = update.message.from_user
    update.message.reply_text('Bye ' + user.first_name + '! Your order is not posted. I hope you would use Cryptocurrency Mart again someday!')

    return telegram.ext.ConversationHandler.END

def wrong_input(update):
    update.message.reply_text('Sorry, I do not recognise that input, type /start to begin again or /cancel to exit.')
    
    return telegram.ext.ConversationHandler.END

def upvote(bot,update):
    text = update.message.text
    user = update.message.from_user.username

    if check_rep_post(user,REP_FILE_PATH,admins) > 0:
        update.message.reply_text('You have exceeded your votes for the past 24 hours!')
        return telegram.ext.ConversationHandler.END

    if text.find('@') != -1:
        voted_user = text[text.find('@')+1::]
        if voted_user == user:
            update.message.reply_text('You cannot vote yourself! Please try again!')
        else:
            repfields = [user,voted_user,1,time.time()]
            # Save reputation data
            file = open(REP_FILE_PATH,'a+',newline='')
            writer = csv.writer(file)
            writer.writerow(repfields)
            file.close()
            reputation_number = rep_count(voted_user,REP_FILE_PATH)
            update.message.reply_text('You have sucessfully upvoted ' + voted_user.replace('_','\\_') + '.\n' + 'The current reputation of ' 
                + voted_user.replace('_','\\_') + ' is *' + str(reputation_number) + '*\nYou are limited to only *ONE vote every 24 hours* to prevent abuse.'
                + 'Type /rep @[Telegram username] to check the reputation of a user',parse_mode=telegram.ParseMode.MARKDOWN)
            if (voted_user != None) and (user != None):
                bot.sendMessage(chat_id=CHAT_ID,text=('@' + user + ' has UPVOTED ' + '@' + voted_user +' for a successful transaction!'))
    else:
        update.message.reply_text('Sorry I do not recognise this input, please type /upvote @[telegram username] to upvote someone.')
    return telegram.ext.ConversationHandler.END

def reputation(bot,update):
    text = update.message.text
    user = update.message.from_user.username
    if text.find('@') != -1:
        queried_user = text[text.find('@')+1::]
        reputation_number = rep_count(queried_user,REP_FILE_PATH)
        update.message.reply_text('The current reputation of ' + queried_user.replace('_','\\_') + ' is: *' + str(reputation_number) + '*\nRemember that all users start out with a reputation of 0!',parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        update.message.reply_text('Sorry I do not recognise this input, please type /rep @[telegram username] to check the reputation of a user. Remember that all users start out with a reputation of 0!')
    return telegram.ext.ConversationHandler.END

def downvote(bot,update):
    text = update.message.text
    user = update.message.from_user.username

    if check_rep_post(user,REP_FILE_PATH,admins) > 0:
        update.message.reply_text('You have exceeded your votes for the past 24 hours!')
        return telegram.ext.ConversationHandler.END

    if text.find('@') != -1:
        voted_user = text[text.find('@')+1::]
        if voted_user == user:
            update.message.reply_text('You cannot vote yourself! Please try again!')
        else:
            repfields = [user,voted_user,-1,time.time()]
            # Save reputation data
            file = open(REP_FILE_PATH,'a+',newline='')
            writer = csv.writer(file)
            writer.writerow(repfields)
            file.close()
            reputation_number = rep_count(voted_user,REP_FILE_PATH)
            update.message.reply_text('You have sucessfully downvoted ' + voted_user.replace('_','\\_') + '.\n' + 'The current reputation of ' 
                + voted_user.replace('_','\\_') + ' is *' + str(reputation_number) + '*\nYou are limited to only *ONE vote every 24 hours* to prevent abuse.\n' 
                + 'Type /rep @[Telegram username] to check the reputation of a user',parse_mode=telegram.ParseMode.MARKDOWN)
            if (voted_user != None) and (user != None):
                bot.sendMessage(chat_id=CHAT_ID,text=('@' + user + ' has DOWNVOTED ' + '@' + voted_user +' for a bad experience!'))
    else:
        update.message.reply_text('Sorry I do not recognise this input, please type /downvote @[telegram username] to downvote someone.')
    return telegram.ext.ConversationHandler.END

def escrow(bot,update):
    update.message.reply_text(
        'To prevent scam activity, we are introducing an escrow system where a broker can act as an ' +
        'intermediary of both fiat and crypto for both parties. '
        'Trusted brokers are vetted members of the channel who can help faciliate a deal for a small fee.\n\n'+
        'Upon finding a matched interest, both buyer and seller can agree to use an escrow service to ensure reliability. '
        'Once both parties have sent the fiat and cryptocurrency, only then, will the broker release the payments.\n\n'
        '*By using our recommended brokers for escrow services, you agree that we are NOT liable for any loss in fiat or cryptocurrencies.*\n\n'
        'Below is our list of trusted brokers:\n' +
        '[Updated 3-Jan 2018]\n'
        '@wuffle - Singapore - SGD\n' +
        '@dotdotc - London, UK - GBP\n' +
        '@starchris4 - Hong Kong - HKD\n' +
        '@nickyong - New York, US - USD\n' +
        '@squesto - New York, US - USD\n',parse_mode=telegram.ParseMode.MARKDOWN)
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
            INIT_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                           init_choice,
                                    pass_user_data=True),
                       ],

            BUY_SELL_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                           buy_sell_choice,
                                    pass_user_data=True),
                       ],

            EXISTING_ORDER_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                           existing_order_choice,
                                    pass_user_data=True),
                       ],

            CRYPTO_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                           crypto_choice,
                                    pass_user_data=True),
                       ],

            PRICE_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                            price_choice,
                                    pass_user_data=True),
                       ],

            FIAT_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text, 
                                            fiat_choice, 
                                    pass_user_data =True)
                       ],

            PAYMENT_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text, 
                                            payment_choice, 
                                    pass_user_data =True)
                       ],

            LOCATION_REQUEST: [telegram.ext.MessageHandler(telegram.ext.Filters.text, 
                                            location_choice, 
                                    pass_user_data =True)
                       ],

            CHECK_INPUT:[telegram.ext.MessageHandler((telegram.ext.Filters.location | telegram.ext.Filters.text),
                                           check_input,
                                    pass_user_data=True)
                       ],

            UPDATE_CUSTOM_LOCATION:[telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                           check_input_location,
                                    pass_user_data=True)
                       ],
                           
            SUBMIT: [telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                          done,
                                          pass_user_data=True)
                       ],                                
        },

        fallbacks=[telegram.ext.CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # Command handlers
    dp.add_handler(telegram.ext.CommandHandler('upvote', upvote))
    dp.add_handler(telegram.ext.CommandHandler('downvote', downvote))
    dp.add_handler(telegram.ext.CommandHandler('rep', reputation))
    dp.add_handler(telegram.ext.CommandHandler('escrow', escrow))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    print("Bot is running... Press Ctrl + C to end it")
    main()