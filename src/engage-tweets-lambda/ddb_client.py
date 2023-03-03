import os
import time

import boto3

dynamodb = boto3.resource('dynamodb')
RepliedTweetsTable = os.getenv("TABLE_NAME")

# Add the replied tweet and the time to DynamoDB
def store_replied_tweet(tweet_id, user_id, reply_tweet_id, search_key, ttl = 604800):
    now = int(time.time())
    dynamodb.Table(RepliedTweetsTable).put_item(
        Item={
            'tweetId': str(tweet_id),
            'userId': str(user_id),
            'replyTweetId': str(reply_tweet_id),
            'searchKey': search_key,
            'TTL': now + ttl
        }
    )

# Check if the tweet has been replied before
def is_tweet_replied(tweet_id, user_id):
    response = dynamodb.Table(RepliedTweetsTable).get_item(
        Key={
            'tweetId': str(tweet_id),
            'userId': str(user_id)
        }
    )
    return 'Item' in response

# Check if we already replied to the user
def is_user_notified(user_id):
    response = dynamodb.Table(RepliedTweetsTable).query(
        KeyConditionExpression='userId = :userId',
        ExpressionAttributeValues={
            ':userId': str(user_id)
        }
    )
    return response['Items'] != []

def get_latest_activity(tweet_search_key):
    response = dynamodb.Table(RepliedTweetsTable).query(
        IndexName='searchKey-tweetId-index',
        KeyConditionExpression='searchKey = :searchKey',
        ExpressionAttributeValues={
            ':searchKey': tweet_search_key
        },
        Limit=1,
        ScanIndexForward=False,
        ProjectionExpression='tweetId'
    )
    if response['Items'] == []:
        return None
    latest_tweet_id = response['Items'][0]['tweetId']
    return latest_tweet_id

