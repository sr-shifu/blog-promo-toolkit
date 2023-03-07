import concurrent.futures
import datetime
import os
import re
import time
from itertools import combinations

import openai
import tweepy
from dotenv import load_dotenv

from ddb_client import (get_latest_activity, is_tweet_replied,
                        is_user_notified, store_replied_tweet)
from parse_blog_article import extract_twitter_metadata, read_all_articles

if 'AWS_LAMBDA_ENV' not in os.environ or os.getenv('AWS_SAM_LOCAL') == 'true':
    # Running locally
    load_dotenv(dotenv_path = '.env.bot')

bearer_token = os.getenv("BEARER_TOKEN")
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
openai.api_key = os.getenv("OPENAI_API_KEY")
search_days_ago_str = os.getenv("SEARCH_INTERVAL_DAYS", default=None)
search_days_ago = int(search_days_ago_str) if search_days_ago_str is not None else None
min_user_followers = int(os.getenv("MIN_USER_FOLLOWERS") or -1)
dry_run = os.getenv("DRY_RUN") == 'True' or False

IGNORE_ACCOUNTS = ['1568305813768515584', '1617979071467769859']

MAX_TWITTER_MESSAGE_LENGTH = 140

client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key = consumer_key,
    consumer_secret = consumer_secret,
    access_token = access_token,
    access_token_secret = access_token_secret,
    wait_on_rate_limit = True
)

if(dry_run == True):
    print("Running in dry-run mode")

def generate_tweet_reply_message(tweet_url, post_url, lang = 'en'):
    prompt = f"Reply to tweet {tweet_url}. Reply must include link to article {post_url} and engage to follow @TheSameTech{' using ' + lang + ' language' if lang != 'en' else ''}. Don't exceed {str(MAX_TWITTER_MESSAGE_LENGTH)} chars"
    completions = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300,
        n=1,
        stop=None,
        temperature=0.7,
    )
    author_id = re.search(r"twitter\.com/([^/]+)/status", tweet_url).group(1)
    return completions.choices[0].text.replace("\n\n", "").replace(f" @{author_id}", "")

def reply_to_tweet(tweet_id, user_id, search_key, message):
    tweet_url = f"https://twitter.com/{str(user_id)}/status/{tweet_id}"
    print(f"Replying to {tweet_url} with '{message}'")
    if(dry_run == True):
        return
    try:
        response = client.create_tweet(in_reply_to_tweet_id=tweet_id, text=message)
        reply_tweet_id=response.data.get('id')
        store_replied_tweet(tweet_id, user_id, reply_tweet_id, search_key, 604800) # 7 days
    except Exception as e:
        print(f"An error occurred while replying to tweet - {e}")

def search_recent_tweets_with_pagination(query, tweet_fields, start_time=None, latest_tweet_id=None, max_results=None):
    tweets = []
    response = client.search_recent_tweets(query=query, max_results=max_results, start_time=start_time, since_id=latest_tweet_id, tweet_fields=tweet_fields)
    tweets.extend(response.data or [])

    while response.meta.get('next_token'):
        response = client.search_recent_tweets(query=query, max_results=max_results, start_time=start_time, since_id=latest_tweet_id, tweet_fields=tweet_fields, next_token=response.meta.get('next_token'))
        tweets.extend(response.data or [])
    # sort tweets in asc order
    return sorted(tweets, key=lambda tweet: tweet["created_at"])

user_followers_cache = {}
def check_user_match(user_id):
    global user_followers_cache
    
    if min_user_followers is None or min_user_followers < 0:
        return True
    
    # Check if the user's followers count is already in the cache
    if user_id in user_followers_cache:
        user_followers = user_followers_cache[user_id]
    else:
        # If not, fetch the user's followers count from the API
        user_followers = client.get_users_followers(id=user_id, max_results=min_user_followers)
        user_followers_cache[user_id] = user_followers
        
    return len(user_followers) >= min_user_followers

def engage_tweets():
    all_posts = read_all_articles('https://thesametech.com', listContainerSelector='.loop-container')
    if(len(all_posts) == 0):
        raise "No posts detected"

    totalEngaged = 0
    for post_url in(all_posts):
        twitter_metadata = extract_twitter_metadata(post_url, tagsSelector='.post-tags')
        if(len(twitter_metadata) == 0):
            print(f"Post {post_url} has no metadata.")
            continue
        keywords, hash_tags, description, *rest = twitter_metadata
        print(f"Promoting blog post: {post_url}.")
        combos = list(combinations(hash_tags, 2))
        for combo in(combos):
            hash_tags_string = " ".join(combo)
            latest_tweet_id = get_latest_activity(hash_tags_string)
            start_time = None
            if latest_tweet_id is None and search_days_ago is not None:
                start_time=(datetime.datetime.now() - datetime.timedelta(days=search_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
            tweets = search_recent_tweets_with_pagination(query=hash_tags_string, max_results = 100, start_time=start_time, latest_tweet_id=latest_tweet_id, tweet_fields=['id', 'author_id', 'created_at', 'in_reply_to_user_id', 'lang'])
            print(f"Found {len(tweets)} tweets with hash tags {hash_tags_string}.")
            for tweet in tweets:
                if tweet.author_id in IGNORE_ACCOUNTS or tweet.in_reply_to_user_id in IGNORE_ACCOUNTS:
                    print(f"Tweet user (either {tweet.author_id} or {tweet.in_reply_to_user_id}) is in ignore list. Skipping the tweet {tweet.id}.")
                    continue
                if is_tweet_replied(tweet.id, tweet.author_id):
                    print(f"Tweet has already been replied. Skipping the tweet {tweet.id}.")
                    continue
                if is_user_notified(tweet.author_id):
                    print(f"User {tweet.author_id} has already been notified. Skipping the tweet {tweet.id}.")
                    continue
                if not check_user_match(tweet.author_id):
                    print(f"User {tweet.author_id} has less than {min_user_followers} followers. Skipping the tweet {tweet.id}.")
                    continue
                tweet_url = f"https://twitter.com/{str(tweet.author_id)}/status/{tweet.id}"
                tweet_reply = f"{description}\n{post_url}"
                try:
                    if dry_run == False:
                        print(f"Generating reply using ChatGPT for tweet {tweet.id} from {tweet.author_id}...")
                        tweet_reply = generate_tweet_reply_message(tweet_url, post_url, tweet.lang)
                    reply_to_tweet(tweet.id, tweet.author_id, hash_tags_string, tweet_reply)
                    totalEngaged+=1
                except Exception as e:
                    print(f"\033[1;31mAn error occurred while replying to tweet {tweet.id} - {e}\033[0m")
                time.sleep(1) # sleep 1sec
    return {"total": totalEngaged}

def start():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(engage_tweets)
    return future

if __name__ == "__main__":
    engage_tweets()
