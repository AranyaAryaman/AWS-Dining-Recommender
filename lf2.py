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

def get_random_restaurants(cuisine, count=3):
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
        return []

    hits = response.json().get("hits", {}).get("hits", [])
    if not hits:
        print(f"No restaurants found for cuisine: {cuisine}")
        return []

    selected_restaurants = random.sample(hits, min(count, len(hits)))
    return [restaurant["_source"]["id"] for restaurant in selected_restaurants]

def get_restaurant_details(restaurant_id, cuisine):
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    response = table.get_item(Key={"id": restaurant_id, "cuisine": cuisine})
    return response.get("Item", {})

def send_email(to_email, restaurants, cuisine, people, dining_time):
    restaurant_lines = [
        f"{i+1}. {r['name']}, located at {r['address']}"
        for i, r in enumerate(restaurants)
    ]

    subject = f"Recommended {cuisine} Restaurants!"
    body_text = f"""
    Hello! Here are my {cuisine} restaurant suggestions for {people} people, for {dining_time}:
    {chr(10).join(restaurant_lines)}
    
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
    restaurant_ids = get_random_restaurants(cuisine)
    logger.info(f"restaurant_ids: {restaurant_ids}")
    
    if not restaurant_ids:
        return {"statusCode": 404, "body": "No restaurants found"}
    
    cuisine = cuisine.capitalize()
    restaurant_details = [
        get_restaurant_details(str(rid), cuisine) for rid in restaurant_ids
    ]
    
    if not all(restaurant_details):
        return {"statusCode": 404, "body": "Some restaurant details missing in DynamoDB"}
    
    send_email(email, restaurant_details, cuisine, people, diningTime)
    
    return {"statusCode": 200, "body": f"Recommendation sent to {email}"}
