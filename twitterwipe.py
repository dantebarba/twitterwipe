import os
import tweepy
import json
import yaml
import logging
import concurrent.futures
import pandas
import click
from dateutil import parser
from datetime import timedelta, datetime

full_path = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(filename=full_path + '/log.log', level=logging.INFO,
                    format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)


def main():
    logger.info('starting twitterwipe')

    config = open_config()

    delete_timestamps = get_delete_timestamps(config)
    purge_activity(delete_timestamps)

    logger.info('done')


def open_config():
    with open(full_path + '/config.yaml', 'r') as yamlfile:
        return yaml.load(yamlfile, Loader=yaml.FullLoader)


def get_delete_timestamps(config):
    curr_dt_utc = datetime.utcnow()

    days = config['days_to_save']
    likes = days['likes']
    retweets = days['retweets']
    tweets = days['tweets']

    likes_delta = timedelta(likes)
    retweets_delta = timedelta(tweets)
    tweets_delta = timedelta(tweets)

    likes_time = curr_dt_utc - likes_delta
    retweets_time = curr_dt_utc - retweets_delta
    tweets_time = curr_dt_utc - tweets_delta

    return (likes_time, retweets_time, tweets_time)


def purge_activity(delete_timestamps):
    api = get_api()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:
        e.submit(delete_tweets, api, delete_timestamps[2])
        e.submit(delete_retweets, api, delete_timestamps[1])
        e.submit(delete_favorites, api, delete_timestamps[0])


def find_tweet_by_id(api, tweet_id):
    try:
        return api.get_status(tweet_id)
    except Exception as e:
        logger.error("failed to find {}".format(tweet_id), exc_info=True)
        return None


def delete_tweet_by_id(api, tweet_id):
    try:
        api.destroy_status(tweet_id)
        return 1
    except Exception as e:
        logger.error("failed to delete {}".format(tweet_id), exc_info=True)
        return 0


def delete_favorite_by_id(api, tweet_id):
    try:
        api.destroy_favorite(tweet_id)
        return 1
    except:
        logger.error('failed to delete favorite'.format(
            tweet_id), exc_info=True)
        return 0


def delete_retweet_by_id(api, tweet_id):
    try:
        api.unretweet(tweet_id)
        return 1
    except:
        logger.error('failed to unretweet {}'.format(tweet_id), exc_info=True)
        return 0


def delete_tweets(api, ts):
    logger.info('deleting tweets before {}'.format(str(ts)))

    count = 0

    for status in tweepy.Cursor(api.user_timeline).items():
        if status.created_at < ts:
            count += delete_tweet_by_id(api, status.id)

    logger.info('{} tweets deleted'.format(count))

    return


def delete_retweets(api, ts):
    logger.info('deleting retweets before {}'.format(str(ts)))

    count = 0

    for status in tweepy.Cursor(api.user_timeline).items():
        if status.created_at < ts:
            count += delete_retweet_by_id(api, status.id)

    logger.info('{} retweets deleted'.format(count))

    return


def delete_favorites(api, ts):
    logger.info('deleting favorites before {}'.format(str(ts)))

    count = 0

    for status in tweepy.Cursor(api.favorites).items():
        if status.created_at < ts:
            count += delete_favorite_by_id(api, status.id)

    logger.info('{} favorites deleted'.format(count))

    return


def get_api():

    try:
        # get keys from os environment variables if they exist
        d = {'consumer_key': os.environ['CONSUMER_KEY'],
             'consumer_secret': os.environ['CONSUMER_SECRET'],
             'app_key': os.environ['APP_KEY'],
             'app_secret': os.environ['APP_SECRET']}
    except KeyError:
        # environment variables are not found, so try the json file instead
        with open(full_path + '/keys.json', 'r') as f:
            d = json.load(f)

    auth = tweepy.OAuthHandler(d['consumer_key'], d['consumer_secret'])
    auth.set_access_token(d['app_key'], d['app_secret'])

    return tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


def get_csv_ids(csv):

    if not csv:
        raise FileNotFoundError("No csv has been loaded")

    return pandas.read_csv(csv, lineterminator='\n')[["tweet.id", "tweet.created_at"]]


def test_string_in_file(json_file, string):
    if (string in json_file.read()):
        raise Exception("Please delete the " + string +
                        " token in the json and then try again")


def check_fixed_json(json_file):
    test_string_in_file(json_file, "window.YTD.like.part")
    test_string_in_file(json_file, "window.YTD.tweet.part")
    json_file.seek(0)


def get_js_ids(js):

    if not js:
        raise FileNotFoundError("No json has been loaded")

    with open(js, 'r', encoding='utf8') as json_file:
        check_fixed_json(json_file)
        return pandas.read_json(json_file)


def delete_tweets_by_id(api, tweets_id, ts):

    logger.info('deleting tweets by id before {}'.format(str(ts)))

    count = 0

    for index, status in tweets_id.iterrows():
        if parser.parse(status["tweet.created_at"]).replace(tzinfo=None) < ts.replace(tzinfo=None):
            count += delete_tweet_by_id(api, status["tweet.id"])

    logger.info('{} tweets by id deleted '.format(count))


def delete_tweets_by_id_js(api, tweets_id, ts):

    logger.info('deleting tweets by id before {}'.format(str(ts)))

    count = 0

    for tweet in tweets_id:
        if parser.parse(tweet["timestamp"]).replace(tzinfo=None) < ts.replace(tzinfo=None):
            count += delete_tweet_by_id(api, tweet["id"])

    logger.info('{} tweets by id deleted '.format(count))


def delete_likes_by_id(api, tweets_id, ts):
    logger.info('deleting likes by id before {}'.format(str(ts)))

    count = 0

    for tweet in tweets_id:
        status = find_tweet_by_id(api, tweet["id"])
        if status and status.created_at.replace(tzinfo=None) < ts.replace(tzinfo=None):
            count += delete_favorite_by_id(api, tweet["id"])

    logger.info('{} likes by id deleted '.format(count))


@click.group()
def actions():
    """
        Welcome to twitterwipe. Please use --help on each
        available command.
    """
    pass


@actions.command()
def wipe_using_api():
    """ 
        This command will wipe all your likes, retweets and tweets
        from your account preceding a certain number of days. Please keep
        in mind that due to Twitter API limitations, 
        this command will only retrive up to 3200 tweets.
    """
    main()


@actions.command()
@click.option('--csv', help='CSV file location', required='true')
def delete_tweets_from_csv(csv):
    """
        This command allows you to delete all your tweets preceding a certain number
        of days taking as input a comma-separated CSV file. This CSV file should have
        two mandatory columns:
            - tweet.id
            - tweet.created_at
    """
    tweets_id = get_csv_ids(csv)

    config = open_config()

    timestamps = get_delete_timestamps(config)

    api = get_api()

    delete_tweets_by_id(api, tweets_id, timestamps[2])

    logger.info('done from csv')


@actions.command()
@click.option('--json', help='tweet.js location', required='true')
def delete_tweets_from_js(json):
    """
        This command allows you to wipe all your tweets preceding a certain number
        of days. It takes as input the tweet.js file. You can get this file by asking for your data
        from Twitter.
    """
    tweets_id = get_js_ids(json)

    config = open_config()

    timestamps = get_delete_timestamps(config)

    api = get_api()

    tweets = map(lambda status: {
                 "id": status[1].tweet["id"], "timestamp": status[1].tweet["created_at"]}, tweets_id.iterrows())

    delete_tweets_by_id_js(api, tweets, timestamps[2])

    logger.info('done from json')


@actions.command()
@click.option('--json', help='like.js location', required='true')
def delete_likes_from_js(json):
    """  
        This command allows you to wipe all your likes preceding a certain number
        of days. It takes as input the like.js file. You can get this file by asking for your data
        from Twitter.
    """
    tweets_id = get_js_ids(json)

    config = open_config()

    timestamps = get_delete_timestamps(config)

    api = get_api()

    tweets = map(lambda status: {
                 "id": status[1].like["tweetId"], "timestamp": None}, tweets_id.iterrows())

    delete_likes_by_id(api, tweets, timestamps[2])

    logger.info('done from json')


if __name__ == '__main__':
    actions().add_command(wipe_using_api)
    actions().add_command(delete_tweets_from_csv)
    actions().add_command(delete_tweets_from_js)
    actions().add_command(delete_likes_from_js)
    actions()
