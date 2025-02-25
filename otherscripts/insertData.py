import boto3
import json
import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yelp-restaurants')  

with open('restaurants.json', 'r') as file:
    restaurants = json.load(file)

for restaurant in restaurants:
    restaurant["latitude"] = Decimal(str(restaurant["latitude"]))
    restaurant["longitude"] = Decimal(str(restaurant["longitude"]))
    restaurant["rating"] = Decimal(str(restaurant["rating"]))

    restaurant["insertedAtTimestamp"] = datetime.datetime.now(datetime.UTC).isoformat()

    try:
        response = table.put_item(Item=restaurant)
        print(f"Inserted: {restaurant['name']}")
    except Exception as e:
        print(f"Error inserting {restaurant['name']}: {str(e)}")
