import json

from engage_tweets import start


def handler(event, context):
    future = start()
    result = future.result()
    return {"statusCode": 200, "body": json.dumps(result)}
