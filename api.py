import configparser
import requests
import re
import inflect
import base64
import hashlib
import hmac
import json
import time
import threading
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1Session
from flask import Flask
from flask import request
import subprocess
import sys
from multiprocessing import Pool


app = Flask(__name__)
config = configparser.ConfigParser()
config.read('credentials.ini')
ord = inflect.engine().ordinal

reply_maps = {}

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

	return f'This text is found on page {page} of the book "{title}" -- the {ord(volume)} volume that sits on the {ord(shelf)} shelf of the {ord(wall)} wall in room {room}: {url}'




def send_dm(text, recipient_id):
	url = 'https://api.twitter.com/1.1/direct_messages/events/new.json'
	event = {
		'event': {
			'type': 'message_create',
			'message_create': {
				'target': {
					'recipient_id': recipient_id
				},
				'message_data': {
					'text': text
				}
			}
		}
	}
	r = twitter.post(url, json=event)
	if r.status_code is not 200:
		print(f'dm failed: {r.text}')


def process_dm_event(dme):
	message = dme['message_create']['message_data']['text']
	recipient_id = dme['message_create']['sender_id']
	print(f'received from {recipient_id}: {message}')
	response = babel(message)
	send_dm(response, recipient_id)

def start_autohook():
	proc = subprocess.Popen(['/bin/bash','autohook.sh'],stdout=subprocess.PIPE,text=True)
	line = ''
	cnt = 0
	while 'Subscribed' not in line and cnt < 10:
		line = str(proc.stdout.readline())
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
			if 'direct_message_events' in event and len(event['direct_message_events']) > 0:
				dme = event['direct_message_events'][0]
				if dme['type'] == 'message_create':
					if dme['message_create']['target']['recipient_id'] == '1215156392673169408':
						dm_thread = threading.Thread(target=process_dm_event, args=(dme,))
						dm_thread.daemon = True
						dm_thread.start()
		except json.JSONDecodeError:
			continue
#
# start_autohook()

def get_tweet(id):
	url = 'https://api.twitter.com/1.1/statuses/show.json'
	r = twitter.get(url, params={'id': id, 'tweet_mode': 'extended'})
	return r.json()


def reply_tweet(content, user_screen_name, status_id):
	url = 'https://api.twitter.com/1.1/statuses/update.json'
	params = {
		'status': f'@{user_screen_name} {content}',
		'in_reply_to_status_id': status_id
	}

	r = twitter.post(url, params=params)
	# print(r.json())


def retweet(id):
	print(f'retweeting: {id}')
	t = get_tweet(id)
	original_text = t['full_text']
	babeled = babel(original_text)

	attachment_url = f"https://www.twitter.com/{t['user']['screen_name']}/status/{t['id']}"

	print(attachment_url)
	status = {
		"status": babeled,
		"attachment_url": attachment_url
	}
	tweet(status)



def start_retweeting():
	while True:
		if len(reply_maps) > 0:
			tweet_id = max(reply_maps, key=lambda x: reply_maps[x])
			print(f'retweeting the most popular tweet at {datetime.datetime.now()}: {tweet_id}')
			retweet(id)

			# sleep for 5 hrs
		time.sleep(5 * 3600)


def process_mentions():
	while True:
		print('checking mentions...')
		url = 'https://api.twitter.com/1.1/statuses/mentions_timeline.json?'

		with open('.last_mention') as f:
			since_id = f.readline()

		if since_id:
			r = twitter.get(url, params={'since_id': since_id})
		else:
			r = twitter.get(url)


		mentions = r.json()
		if 'errors' in mentions:
			print(mentions)
		elif len(mentions) > 0:
			print(mentions)
			since_id = mentions[0]['id']

		for mention in mentions:
			id = mention['id']
			if mention['in_reply_to_status_id']:
				user_screen_name = mention['user']['screen_name']

				# Override myself
				print(user_screen_name)
				if user_screen_name == 'Simonl2507':
					dm_thread = threading.Thread(target=retweet, args=(mention['in_reply_to_status_id',))
					dm_thread.daemon = True
					dm_thread.start()

				original_text = get_tweet(mention['in_reply_to_status_id'])['full_text']
				babeled = babel(original_text)
				reply_tweet(babeled, user_screen_name, id)

				# update response map
				if mention['in_reply_to_status_id'] not in reply_maps:
					reply_maps[mention['in_reply_to_status_id']] = 1
				reply_maps[mention['in_reply_to_status_id']]

		with open('.last_mention', 'w') as f:
			f.write(str(since_id))

		time.sleep(12)



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


mentions_thread = threading.Thread(target=process_mentions)
mentions_thread.daemon = True
mentions_thread.start()

retweet_thread = threading.Thread(target=start_retweeting)
retweet_thread.daemon = True
retweet_thread.start()

retweet_thread.join()

# start_autohook()
