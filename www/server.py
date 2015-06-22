import os
import ConfigParser
import requests
from bson.json_util import dumps
from bson.objectid import ObjectId
from bson import BSON
from bson import json_util
from flask import Flask,render_template,request
from pymongo import MongoClient 
from random import randint
import json


app = Flask(__name__)
app.debug = True


# constants
CONFIG_FILENAME = 'app.config'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# read in app config
config = ConfigParser.ConfigParser()
config.read(os.path.join(BASE_DIR,CONFIG_FILENAME))

# MongoDB & links to each collection
#uri = "mongodb://"+ config.get('db','user')+ ":"+ config.get('db','pass')+"@" +config.get('db','host') + ":" + config.get('db','port')+"/?authSource="+config.get('db','auth_db')
uri = "mongodb://"+config.get('db','host')+":"+ config.get('db','port')
db_client = MongoClient(uri)
app.db = db_client[config.get('db','name')]
app.db_weather_collection = app.db[config.get('db','weather_collection')]
app.db_jokes_collection = app.db[config.get('db','jokes_collection')]

@app.route('/')
def hello_world():
    return 'Hello I am the future home of The Babbling Brook Jokes API! Funniness to come.'

# Will query the Wunderground API for all the locations we need (Tidmarsh & MIT to start) and save each reading to the MongoDB
# This will be called from a cron job that runs every 15 minutes
@app.route('/saveWeatherData')
def save_weather_data():
	url = 'http://api.wunderground.com/api/' + config.get('api','wunderground_key') + '/conditions/q/MA/Plymouth.json'
	response = requests.get(url)

	app.db.weather_collection.insert(response.json())
	return response.content

# Saves sensor data posted to the DB, make sure you send with Content-Type: json
@app.route('/saveSensorData')
def save_sensor_data():
	content = request.get_json()
	if content is not None:
		app.db.weather_collection.insert(content)
		return "OK"
	else:
		return "Error: Your post needs to be formatted as JSON and the Content Type needs to be 'json'"


# Grabs latest data from DB and tells a joke
# TODO: save the mp3 file to our server so we can reload without going to the API
@app.route('/tellAJoke')
def tell_a_joke():
	
	# Grab latest weather data from DB
	result= app.db.weather_collection.find().sort([["_id",-1]]).limit(1)
	if result.count() == 0:
		return "no data in the database"
	else:
		result = result.next()

		# Joke Logic - TBD Better. Only working on temp at the moment. 
		temp = float(result["current_observation"]["temp_f"])
		#jokes = app.db.jokes_collection.find({ "$or" : [{"conditions.temp_f.is_greater_than" : {"$lt":temp}}, {"conditions.temp_f.is_less_than" : {"$gt":temp}}, {"conditions.temp_f.is_equal_to" : {"$eq":temp}} ]},{"joke":1})
		jokes = app.db.jokes_collection.find({ "$or" : [{"conditions.temp_f.is_greater_than" : {"$lt":temp}}, {"conditions.temp_f.is_less_than" : {"$gt":temp}} ]},{"joke":1})

		if jokes.count() == 0:
			joke = "hey there is no joke here because the developer is not very funny. Hahahahahaha."	
		else:
			random = randint(0,jokes.count()-1)
			print random
			if (random == 0):
				joke = jokes.next()["joke"]
			else:
				joke = jokes.skip(random).next()["joke"]

		print joke
		
		# Send out for TTS
		audio_url = "http://tts-api.com/tts.mp3"
		params = {"q":joke, "return_url":1}
		print audio_url
		response = requests.get(audio_url, params=params)
		audio_html = '<audio controls autoplay><source src="'+ response.content +'" type="audio/mpeg">Your browser does not support the audio element.</audio>'

		# Dump raw data so we can verify it's working
		r = {}
		r["audio_url"] = response.content
		r["joke"] = joke
		r["current_observation"] = {}
		r["current_observation"]["temp_f"]=temp
		json = dumps(r,sort_keys=True, indent=4)

		# Return all that
		#return audio_html + "<h1>"+joke+"</h1> <pre style=\"white-space: pre-wrap;\">" + json + "</pre>"
		return json

# Interface to input new jokes based on conditional parameters
@app.route('/writeAJoke', methods=['GET', 'POST'])
def write_a_joke():

	if request.method == 'POST':
		variable = request.form['variable']
		isGreaterThan = request.form['is_greater_than']
		variableValue = request.form['variable_value']
		joke = request.form['joke']

		#todo - make this more robust, use regex
		joke = joke.replace("((temperature))",variableValue)
		joke = joke.replace("((windspeed))",variableValue)

		error_message = ""
		if variableValue == None or variableValue == "":
			error_message = "Need to specify a value"
		if joke == None or joke == "" or joke == "Funny Joke":
			error_message = "Need to specify a joke if you want comedy"
		if error_message == "":
			data = {}
			data['joke'] = joke
			data['conditions'] = {}
			data['conditions'][variable] = {}
			data['conditions'][variable][isGreaterThan] = int(variableValue) 
			
			app.db.jokes_collection.insert(data)
		return render_template('writeAJoke.html', joke=joke, variable=variable, is_greater_than=isGreaterThan,variable_value=variableValue, error_message=error_message)
	else: 
		return render_template('writeAJoke.html')

# JSON data dump based on parameter OR parameters of interest
# create list 
# visualize a parameter of interest
# pull all of those and graph them with googlecharts
# return timestamp and list of parameters, 1-n, that have TEMP AND HUMIDITY
@app.route('/dataDump', methods=['GET', 'POST'])
def datadump():
	result=[]
	listOfParams = request.args.get("listOfParams")
	if listOfParams is None:
		return "ERROR: Send me the variable 'listOfParams' with the names of variables of interest. If you need to see names of variables of interest check here: /saveWeatherData. Don't send current_observation.temp_f, just send temp_f"
	else: 
		theList = listOfParams.split(",")
		firstThing = theList[0]

		q = app.db.weather_collection.find({ firstThing : {"$exists":'true'} }, {firstThing:1, "current_observation.observation_time_rfc822":1, "current_observation.observation_epoch":1 }).sort([("current_observation.observation_epoch",1)])
		
		for row in q:
			result.append(row)
	return json.dumps(result, sort_keys=True, indent=4, default=json_util.default)

@app.route('/datavizGrid', methods=['GET', 'POST'])
def visualize():
	# pull out data we want to  see
	# format it for google
	# send to google
	# print response 
	# google charts and print out a grid of temp, conductivity etc over the last x period of time
	hi = "hi"

if __name__ == '__main__':
    app.run()























