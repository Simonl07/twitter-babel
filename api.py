import configparser
import requests
import re
import inflect
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1Session
from flask import Flask


app = Flask(__name__)

@app.route('/test')
def hello_world():
	return 'Hello, World!'

bio = "The babel librarian of Twitter. Unraveling the location of tweets around the world and the messages of curious visitors."
config = configparser.ConfigParser()
config.read('credentials.ini')

ord = inflect.engine().ordinal

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
app.run(host='', port=80, debug=True)
# dm_default_welcome_message("Welcome!")
# tweet({"status": "hello world3 attachment_url", "attachment_url": "https://twitter.com/andypiper/status/903615884664725505"})
