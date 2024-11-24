import requests
import time
import csv
import os
import random

# Yelp API key
api_key = 'qDhtGGUl6f8kENMzN0qCIaoDuNjO6xhagyBMFnom2Wp2RL-Ps9Yn5M5Tw3U52q2tQyf8gHKJbV61fRtvUui0DBcFkE7RVujUgnxdXurSdQB5XypW44lr03qKSqBCZ3Yx'

# Search parameters
location = '10003'  # Postal code 10003 for NYC
term = 'restaurant'  
max_results = 100  # Limit results to reduce requests
max_reviews_per_restaurant = 1  

# Yelp API headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

# Function to search for restaurants, optimized with specific neighborhood keywords
def search_restaurants(location, term, limit=50, offset=0):
    # Add specific neighborhood keywords to the search term
    neighborhoods = ['East Village', 'Union Square', 'Gramercy']
    term_with_neighborhood = f"{term} {' '.join(neighborhoods)}"  # Combine the keywords into the search term
    
    # Yelp API URL with specific location and terms
    search_url = f"https://api.yelp.com/v3/businesses/search?location={location}&term={term_with_neighborhood}&limit={limit}&offset={offset}"
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()  # Raise for non-200 responses
        return response.json().get('businesses', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching businesses: {e}")
        return []

# Function to get reviews for a specific business
def get_reviews(business_id):
    reviews_url = f"https://api.yelp.com/v3/businesses/{business_id}/reviews?limit={max_reviews_per_restaurant}"
    try:
        response = requests.get(reviews_url, headers=headers)
        response.raise_for_status()
        return response.json().get('reviews', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews for {business_id}: {e}")
        return []

# Function to fetch businesses and their reviews (up to max_results)
def fetch_business_reviews(location, term, max_results=100):
    all_reviews = []
    seen_business_ids = set()  # Set to track processed businesses
    
    # Calculate how many pages of results we need to fetch
    pages_needed = (max_results // 50) + (1 if max_results % 50 != 0 else 0)
    
    for page in range(pages_needed):
        offset = page * 50  # Update offset for pagination
        businesses = search_restaurants(location, term, limit=50, offset=offset)
        
        if not businesses:
            print("No more businesses found, ending request.")
            break
        
        for business in businesses:
            business_id = business['id']
            if business_id in seen_business_ids:
                continue  # Avoid duplicate requests
            seen_business_ids.add(business_id)
            
            print(f"\nFetching reviews for {business['name']}...")
            reviews = get_reviews(business_id)

            if reviews:
                all_reviews.append({
                    'business_name': business['name'],
                    'review_text': reviews[0]['text']
                })

            # Sleep to prevent hitting the rate limit
            time.sleep(4)  # Add random sleep time

    return all_reviews

# Function to write the fetched reviews to a CSV file
def write_to_csv(reviews, filename="restaurants_reviews.csv"):
    script_dir = os.path.dirname(os.path.realpath(__file__))  # Get the script's directory
    file_path = os.path.join(script_dir, filename)
    
    fieldnames = ['business_name', 'review_text']
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()  # Write the header row
        
        for review_data in reviews:
            writer.writerow({
                'business_name': review_data['business_name'],
                'review_text': review_data['review_text']
            })
    
    print(f"Reviews saved to {file_path}")

# Main execution to fetch and save reviews
reviews = fetch_business_reviews(location, term, max_results)
write_to_csv(reviews)
