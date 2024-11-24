import requests
import time

# Replace 'your_api_key_here' with your actual Yelp API key
api_key = '01WSezkCpEgpErRuKeMXYJRvqrRvcYabzUn9lI-T65FCWnxIAmkicY8os8mx8LRDKn7f2Exg4usa5Mdm1FudBVWuTF5jVGkaYQ2UcuHfOIxb7dwYf3seYLyuwZJCZ3Yx'

# Location and term for search
location = '10003'  # Postal code 10003 for NYC
term = 'restaurant'  # Searching specifically for restaurants
max_results = 100  # Get up to 100 results (2 calls with 50 restaurants per call)
max_reviews_per_restaurant = 1  # Limit to 1 review per restaurant to reduce calls

# Yelp API headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

# Step 1: Search for restaurants in postal code 10003 (only 50 results max per call)
def search_restaurants(location, term, limit=50):
    search_url = f"https://api.yelp.com/v3/businesses/search?location={location}&term={term}&limit={limit}"
    response = requests.get(search_url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('businesses', [])
    else:
        print(f"Error fetching businesses. Status code: {response.status_code}")
        return []

# Step 2: Get a limited number of reviews (1 review per restaurant)
def get_reviews(business_id):
    reviews_url = f"https://api.yelp.com/v3/businesses/{business_id}/reviews?limit={max_reviews_per_restaurant}"
    response = requests.get(reviews_url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('reviews', [])
    else:
        print(f"Error fetching reviews for {business_id}. Status code: {response.status_code}")
        return []

# Step 3: Fetch all businesses and reviews (up to 100 restaurants with reviews)
def fetch_business_reviews(location, term, max_results=100):
    all_reviews = []
    
    # Get 50 restaurants from the first API call
    businesses = search_restaurants(location, term, limit=50)
    
    # If more restaurants exist, make the second call
    if len(businesses) < max_results:
        businesses += search_restaurants(location, term, limit=50)
    
    # Limit the number of restaurants to `max_results` (maximum 100)
    businesses = businesses[:max_results]
    
    for business in businesses:
        business_id = business['id']
        print(f"\nFetching reviews for {business['name']} (ID: {business_id})...")
        
        # Fetch 1 review for each business
        reviews = get_reviews(business_id)

        if reviews:
            all_reviews.append({
                'business_name': business['name'],
                'reviews': reviews
            })

        # Sleep to avoid hitting the rate limit
        time.sleep(1)  # Sleep for 1 second between requests to avoid rate limiting

    return all_reviews

# Run the function to get businesses and their reviews
reviews = fetch_business_reviews(location, term, max_results)

# Print the fetched reviews
for review_data in reviews:
    print(f"\nReviews for {review_data['business_name']}:")
    for review in review_data['reviews']:
        print(f"- {review['text']}")
