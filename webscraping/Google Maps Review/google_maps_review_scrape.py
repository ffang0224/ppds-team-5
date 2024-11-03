import csv
import requests
import os

# Manually load environment variables from .env file
def load_env_variables(file_path="../.env"):
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Load environment variables
load_env_variables()

# Access the API key from the environment
API_KEY = os.getenv("API_KEY")
NUMBER_OF_REVIEWS = 50

def fetch_reviews(api_key, data_id=None, place_id=None, hl='en', sort_by='newestFirst', num=10, max_reviews=50):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps_reviews",
        "api_key": api_key,
        "hl": hl,
        "sort_by": sort_by
    }

    if data_id:
        params["data_id"] = data_id
    elif place_id:
        params["place_id"] = place_id
    else:
        raise ValueError("Either 'data_id' or 'place_id' must be provided")

    print("Writing results to the csv file")
    with open("google_maps_reviews.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["User", "Rating", "Date", "Review", "Likes", "User Profile Link"])

        next_page_token = None
        total_reviews = 0

        while total_reviews < max_reviews:
            if next_page_token:
                params["next_page_token"] = next_page_token
                params["num"] = num
            else:
                params.pop("num", None)

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                reviews = data.get("reviews", [])
                
                for review in reviews[:max_reviews - total_reviews]:
                    user_name = review.get("user", {}).get("name", "Unknown User")
                    rating = review.get("rating", "No Rating")
                    date = review.get("date", "No Date")
                    snippet = review.get("snippet", "No Review Text Available")
                    likes = review.get("likes", 0)
                    user_profile_link = review.get("user", {}).get("link", "No Link")

                    writer.writerow([user_name, rating, date, snippet, likes, user_profile_link])
                    total_reviews += 1

                    if total_reviews >= max_reviews:
                        break

                next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
                if not next_page_token:
                    break
            else:
                print(f"Error: {response.status_code}, {response.text}")
                break

def get_data_id(api_key, search_query):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps",
        "q": search_query,
        "api_key": api_key
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        # ******************************** [0] here gets the first restaurant data that appears on the result list
        place_data = data.get("local_results", [{}])[0]
        data_id = place_data["data_id"]
        return data_id
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# Usage
api_key = API_KEY
search_query = "Joe's Pizza, NYC"
data_id = get_data_id(api_key, search_query)
fetch_reviews(api_key=api_key, data_id=data_id, max_reviews=NUMBER_OF_REVIEWS)
