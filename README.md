# blog-promo-helper
 Toolkit for promoting [TheSameTech](https://thesametech.com/) blog. Contains the following tools:
 - EngageTweets: respond to tweets with relevant content using ChatGPT AI language
 - More tools are coming...


 **NOTE:** find more details in my [article](https://thesametech.com/automated-blog-promotion-with-chatgpt-twitter-and-aws/).

## Running locally

### Using SAM CLI

```bash
sam build
sam local start-lambda
aws lambda invoke --function-name "EngageTweets" --endpoint-url "http://127.0.0.1:3001" --no-verify-ssl out.txt
```


### Using python

 `engage_tweets.py` tool:

 ```bash
cd src/engage-tweets-lambda
pip install -r requirements.txt 
source env/bin/activate   
TABLE_NAME=<TableName> python engage_tweets.py
 ```

### DynamoDB local instance

By default, toolkit will connect to the AWS DynamoDB table. If you want to use local instance, follow these steps:

1. Install required dependencis (do it once in your first setup): *pip install -r requirements.txt*
1. Create Docker network (do it once in your first setup): *docker network create blog-promo-net*
1. Start DynamoDB Local by executing the following at the command prompt:  
	*docker run -p 8000:8000 --network blog-promo-net --name ddblocal amazon/dynamodb-local*  
    This will run the DynamoDB local in a docker container at port 8000.  
1. At the command prompt, list the tables on DynamoDB Local by executing:  
    *aws dynamodb list-tables --endpoint-url http://localhost:8000*  
1. An output such as the one shown below confirms that the DynamoDB local instance has been installed and running:  
    *{*  
      *"TableNames": []*   
    *}*    
1. At the command prompt, create the ToDosTable by executing:  
    *DDB_ENDPOINT=http://localhost:8000 python scripts/create_tables.py*  
      
      **Note:** If you misconfigured your table and need to delete it, you may do so by executing the following command:  
        *aws dynamodb delete-table --table-name ToDosTable --endpoint-url http://localhost:8000*  
1. At the command prompt, start the local API Gateway instance by executing:  
    *sam local start-lambda --docker-network blog-promo-net*  

## Deployment

```bash
sam deploy
```




