import requests
import json

# Your Yelp API Key
API_KEY = "HfZTI3f_YBdl_SK1JasCAD_AyYshlLfVcu3LNX5K6nEDs8v1sGlKe64F9BFEkHBpTGUOMzQRBMOtBWeT_uVK1GQdQyn3cyJF9WCopnGJjUfAEqximS79VlqbeNK4Z3Yx"

# Yelp API Endpoint
YELP_API_URL = "https://api.yelp.com/v3/businesses/search"

# Headers for Authorization
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Cuisines to search for
CUISINES = ["Indian", "Thai", "Chinese", "Mexican", "Kosher", "Continental"]

def fetch_restaurants(cuisine, location="Manhattan", limit=50):
    """
    Fetches up to `limit` restaurants of a given cuisine in the specified location.
    """
    params = {
        "term": f"{cuisine} restaurant",
        "location": location,
        "limit": limit,
        "sort_by": "rating"
    }

    response = requests.get(YELP_API_URL, headers=HEADERS, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get("businesses", [])
    else:
        print(f"Error fetching {cuisine} restaurants: {response.status_code} - {response.text}")
        return []

def save_restaurants_to_file(filename="restaurants.json"):
    """
    Fetches 50 restaurants for each cuisine in Manhattan and saves results to a JSON file.
    """
    all_restaurants = []

    for cuisine in CUISINES:
        restaurants = fetch_restaurants(cuisine)

        for r in restaurants:
            restaurant_data = {
                "cuisine": cuisine,
                "id": r["id"],
                "name": r["name"],
                "rating": r["rating"],
                "address": ", ".join(r["location"]["display_address"]),
                "phone": r.get("phone", "N/A"),
                "latitude": r["coordinates"]["latitude"],
                "longitude": r["coordinates"]["longitude"],
                "zipcode": r["location"]["zip_code"],
                "totalReviews": r["review_count"]
            }
            all_restaurants.append(restaurant_data)

    # Save to JSON file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_restaurants, f, indent=2)

    print(f" Data saved to {filename}")

if __name__ == "__main__":
    save_restaurants_to_file()
