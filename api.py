import configparser
from requests_oauthlib import OAuth1Session


config = configparser.ConfigParser()
config.read('credentials.ini')


twitter = OAuth1Session(
			config['DEFAULT']['oauth_consumer_key'],
			client_secret=config['DEFAULT']['oauth_consumer_secrete'],
			resource_owner_key=config['DEFAULT']['resource_owner_key'],
			resource_owner_secret=config['DEFAULT']['resource_owner_secret']
		)


def tweet(params):
	url = "https://api.twitter.com/1.1/statuses/update.json"
	twitter.post(url, params=params)

tweet({"status": "hello world"})
