import boto3
import os

endpoint_url= os.getenv("DDB_ENDPOINT")
dynamodb = boto3.resource('dynamodb', endpoint_url = endpoint_url)
dynamodb_client = boto3.client('dynamodb', endpoint_url = endpoint_url)

replied_tweets_table_name = 'PromotedTweets'

# Define the schema for the RepliedTweets table
replied_tweets_table = dynamodb.create_table(
    TableName=replied_tweets_table_name,
    KeySchema=[
        {
            'AttributeName': 'userId',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'tweetId',
            'KeyType': 'RANGE'
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'userId',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'tweetId',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'searchKey',
            'AttributeType': 'S'
        }
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    },
     GlobalSecondaryIndexes=[
        {
            'IndexName': 'searchKey-tweetId-index',
            'KeySchema': [
                {
                    'AttributeName': 'searchKey',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'tweetId',
                    'KeyType': 'RANGE'
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL'
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 3,
                'WriteCapacityUnits': 3
            }
        }
    ]
)

# Wait for the table to be created
replied_tweets_table.meta.client.get_waiter('table_exists').wait(TableName=replied_tweets_table_name)

# Enable TTL for the table
dynamodb_client.update_time_to_live(
    TableName=replied_tweets_table_name,
    TimeToLiveSpecification={
        'Enabled': True,
        'AttributeName': 'TTL'
    }
)


# Describe the table to check its status
replied_tweets_table = dynamodb.Table(replied_tweets_table_name)


print(replied_tweets_table.table_status)
