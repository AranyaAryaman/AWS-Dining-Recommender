import json
import requests
from collections import defaultdict
from requests.auth import HTTPBasicAuth

# OpenSearch Configuration
OPENSEARCH_URL = "https://search-restaurant-domain-2f6su7fjpp7fuiubfpxyr6svhe.aos.us-east-1.on.aws"
AUTH = HTTPBasicAuth("aranya", "Aranya289#")  # Use IAM-based auth if needed

# Load restaurants.json
with open("restaurants.json", "r") as file:
    restaurants = json.load(file)

# Group restaurants by cuisine
cuisine_dict = defaultdict(list)
for restaurant in restaurants:
    cuisine_dict[restaurant["cuisine"]].append({
        "id": restaurant["id"],
        "cuisine": restaurant["cuisine"]
    })

# Select only 25 restaurants per cuisine
filtered_restaurants = []
for cuisine, restaurant_list in cuisine_dict.items():
    filtered_restaurants.extend(restaurant_list[:25])  # Pick first 25

# Prepare bulk insert data
bulk_data = ""
for restaurant in filtered_restaurants:
    bulk_data += json.dumps({ "index": { "_index": "restaurants", "_id": restaurant["id"] } }) + "\n"
    bulk_data += json.dumps(restaurant) + "\n"

# Push data to OpenSearch
headers = {"Content-Type": "application/json"}
response = requests.post(f"{OPENSEARCH_URL}/_bulk", data=bulk_data, headers=headers, auth=AUTH)

# Print response
print(response.json())

