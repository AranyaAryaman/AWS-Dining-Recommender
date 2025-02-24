import json
import boto3
import random
import requests
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Services
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

DYNAMODB_TABLE_NAME = "yelp-restaurants"
OPENSEARCH_URL = "https://search-restaurant-domain-2f6su7fjpp7fuiubfpxyr6svhe.aos.us-east-1.on.aws"
OPENSEARCH_USER = "aranya"
OPENSEARCH_PASSWORD = "Aranya289#"
SENDER_EMAIL = "softwarelab25@gmail.com"
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/222634405207/dining-bot"

def get_sqs_message():
    response = sqs.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20)
    logger.info(f"Response: {response}")
    messages = response.get("Messages", [])
    if not messages:
        print("No messages in queue")
        return None

    message = messages[0]
    receipt_handle = message["ReceiptHandle"]
    
    body = json.loads(message["Body"])
    cuisine = body.get("Cuisine", "").strip()
    email = body.get("Email", "").strip()
    diningTime = body.get("DiningTime", "").strip()
    people = body.get("NumberOfPeople", "").strip()
    location = body.get("Location", "").strip()
    logger.info(f"cuisine: {cuisine}, email: {email}, location: {location}, people: {people}, diningTime: {diningTime}")
    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
    
    return cuisine, email, diningTime, people, location

def get_random_restaurant(cuisine):
    query = {
        "size": 25,
        "query": {
            "match": {
                "cuisine": cuisine
            }
        }
    }

    response = requests.get(
        f"{OPENSEARCH_URL}/restaurants/_search",
        auth=HTTPBasicAuth(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        json=query
    )

    if response.status_code != 200:
        print("Error fetching from OpenSearch:", response.text)
        return None
    
    hits = response.json().get("hits", {}).get("hits", [])
    if not hits:
        print(f"No restaurants found for cuisine: {cuisine}")
        return None

    random_restaurant = random.choice(hits)["_source"]
    return random_restaurant["id"]

def get_restaurant_details(restaurant_id, cuisine):
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    response = table.get_item(Key={"id": restaurant_id, "cuisine": cuisine})
    return response.get("Item", {})

def send_email(to_email, restaurant):
    subject = f"Recommended {restaurant['cuisine']} Restaurant!"
    body_text = f"""
    Here is your {restaurant['cuisine']} restaurant recommendation:

    Name: {restaurant['name']}
    Address: {restaurant['address']}
    Phone: {restaurant['phone']}
    Rating: {restaurant['rating']}
    Reviews: {restaurant['totalReviews']}
    Zip: {restaurant['zipcode']}
    Latitude: {restaurant['latitude']}
    Longitude: {restaurant['longitude']}

    Enjoy your meal!
    """

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body_text}}
        }
    )
    print(f"Email sent to {to_email}")

def lambda_handler(event, context):
    message = get_sqs_message()
    if not message:
        return {"statusCode": 400, "body": "No valid message in queue"}
    
    cuisine, email, diningTime, people, location = message
    restaurant_id = get_random_restaurant(cuisine)
    logger.info(f"restaurant_id: {restaurant_id}")
    
    if not restaurant_id:
        return {"statusCode": 404, "body": "No restaurant found"}
    restaurant_id = str(restaurant_id) 
    cuisine = str(cuisine)
    cuisine = cuisine.capitalize()
    logger.info(f"restaurant_id: {restaurant_id}, cuisine: {cuisine}")
    restaurant = get_restaurant_details(restaurant_id, cuisine)
    if not restaurant:
        return {"statusCode": 404, "body": "Restaurant details missing in DynamoDB"}
    
    send_email(email, restaurant)
    
    return {"statusCode": 200, "body": f"Recommendation sent to {email}"}
