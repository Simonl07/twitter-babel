import configparser
import requests
import re
import inflect
import base64
import hashlib
import hmac
import json
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1Session
from flask import Flask
from flask import request
import subprocess
import sys
from json_stream_parser import load_iter


def process_event(event):
    print(event)

proc = subprocess.Popen(['/bin/bash','autohook.sh'],stdout=subprocess.PIPE,text=True)
line = ''
cnt = 0
while 'Subscribed' not in line and cnt < 10:
    line = str(proc.stdout.readline())
    print(line)
    cnt+=1

buff = ''
while True:
    line = proc.stdout.readline()
    if not line:
        break
    buff += line

    try:
        event = json.loads(buff)
        buff = ''
        process_event(event)
    except json.JSONDecodeError:
        continue

#while True:  
    #    line = proc.stdout.readline()
#    if not line:
#        break
#    #the real code does filtering here
#    print("test:", line.rstrip())

app = Flask(__name__)
config = configparser.ConfigParser()
config.read('credentials.ini')
ord = inflect.engine().ordinal


# Twitter webhook challenge
@app.route('/webhooks/twitter', methods=['GET'])
def webhook_challenge():
	# creates HMAC SHA-256 hash from incomming token and your consumer secret

	validation = hmac.new(
		key=bytes(config['DEFAULT']['oauth_consumer_secrete'], 'utf-8'),
		msg=bytes(request.args['crc_token'], 'utf-8'),
		digestmod = hashlib.sha256
	)
	digested = base64.b64encode(validation.digest())

	response = {
		'response_token': 'sha256=' + format(str(digested)[2:-1])
	}

	print('responding to CRC call: ' + str(response))
	return json.dumps(response)


bio = "The babel librarian of Twitter. Unraveling the location of tweets around the world and the messages of curious visitors."

twitter = OAuth1Session(
			config['DEFAULT']['oauth_consumer_key'],
			client_secret=config['DEFAULT']['oauth_consumer_secrete'],
			resource_owner_key=config['DEFAULT']['resource_owner_key'],
			resource_owner_secret=config['DEFAULT']['resource_owner_secret']
		)




def babel(text):
	regex = r"(?P<room>.+?)-w(?P<wall>\d+?)-s(?P<shelf>\d+?)-v(?P<volume>\d+?)$"
	full_room_regex = "postform\('(.+?)'.+?\)"

	url = "https://libraryofbabel.info/search.cgi"
	data = {'find': text, 'btnSubmit': 'Search', 'method': 'x'}
	r = requests.post(url, data=data)
	soup = BeautifulSoup(r.text, features="html.parser")
	exact_match = soup.find_all('div', class_='location')[0].pre
	title = exact_match.find_all('b')[0].get_text()

	location_str = exact_match.a.get_text()
	full_room_hex = re.search(full_room_regex, exact_match.a.get('onclick')).group(1)
	m = re.search(regex, location_str)

	room = m.group('room')
	wall = int(m.group('wall'))
	shelf = int(m.group('shelf'))
	volume = int(m.group('volume'))
	page = int(exact_match.find_all('b')[1].get_text())

	book_marker_url = "https://libraryofbabel.info/bookmarker.cgi"
	book_marker_payload = {
		'hex': full_room_hex,
		'wall': wall,
		'shelf': shelf,
		'volume': m.group('volume'),
		'page': page,
		'title': title + str(page)
	}

	headers = {
		'referer': 'https://libraryofbabel.info/book.cgi',
	}

	r = requests.post(book_marker_url,data=book_marker_payload, headers=headers)
	url = r.url

	print(f'The text "{text}" is found on page {page} of the book "{title}", which is the {ord(volume)} volume that sits on the {ord(shelf)} shelf of the {ord(wall)} wall in room {room}, link to this page: \n {url}')




def tweet(params):
	url = "https://api.twitter.com/1.1/statuses/update.json"
	r = twitter.post(url, params=params)
	print(r.text)

def dm_default_welcome_message(message):
	url = "https://api.twitter.com/1.1/direct_messages/welcome_messages/new.json"
	body = {"welcome_message": {
					"message_data": {
						"text": message,
					}
				}
			}
	r = twitter.post(url, json=body)
	print(r.json()['welcome_message']['id'])

	rule = {"welcome_message_rule": {"welcome_message_id": r.json()['welcome_message']['id']}}
	url = "https://api.twitter.com/1.1/direct_messages/welcome_messages/rules/new.json"
	r = twitter.post(url, json=rule)


babel('hello world abcde')
#
print("starting babel-bot instance")
app.run(host='0.0.0.0', port=80)
# dm_default_welcome_message("Welcome!")
# tweet({"status": "hello world3 attachment_url", "attachment_url": "https://twitter.com/andypiper/status/903615884664725505"})
