import os
import ConfigParser
from pymongo import MongoClient 
import requests
from flask import Flask

app = Flask(__name__)
app.debug = True


# constants
CONFIG_FILENAME = 'app.config'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# read in app config
config = ConfigParser.ConfigParser()
config.read(os.path.join(BASE_DIR,CONFIG_FILENAME))

# MongoDB & links to each collection
uri = "mongodb://"+ config.get('db','user')+ ":"+ config.get('db','pass')+"@" +config.get('db','host') + ":" + config.get('db','port')+"/?authSource="+config.get('db','auth_db')
db_client = MongoClient(uri)
app.db = db_client[config.get('db','name')]
#app.db_weather_collection = app.db[config.get('db','weather_collection')]

@app.route('/')
def hello_world():
    return 'Hello I am the future home of The Babbling Brook! Funniness to come.'

# Will query the Wunderground API for all the locations we need (Tidmarsh & MIT to start) and save each reading to the MongoDB
# This will be called from a cron job that runs every 15 minutes
@app.route('/saveWeatherData')
def save_weather_data():
	url = 'http://api.wunderground.com/api/' + config.get('api','wunderground_key') + '/conditions/q/MA/Plymouth.json'
	response = requests.get(url).content
	app.db.weather_collection.insert([response])
	return requests.get(url).content

if __name__ == '__main__':
    app.run()