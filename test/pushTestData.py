
import sys, os, argparse
import json
import requests



value = 75
#print value

babble_url = 'http://127.0.0.1:5000/saveSingleObservation'
data = {'current_observation': {'temp_f':value}}

headers = {'Content-type': 'application/json','Accept': 'text/plain'}
r = requests.post(babble_url, data = json.dumps(data), headers = headers)
print r
