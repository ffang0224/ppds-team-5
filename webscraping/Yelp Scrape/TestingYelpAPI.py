import requests
import time
import csv
import os
import random


api_key = 'qDhtGGUl6f8kENMzN0qCIaoDuNjO6xhagyBMFnom2Wp2RL-Ps9Yn5M5Tw3U52q2tQyf8gHKJbV61fRtvUui0DBcFkE7RVujUgnxdXurSdQB5XypW44lr03qKSqBCZ3Yx'


location = '10003'  # Postal code 10003 for NYC
term = 'restaurant'  
max_results = 458  # Limit to 100 results to reduce load
max_reviews_per_restaurant = 1  

# Yelp API headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

# Step 1: Search for restaurants in postal code 10003 (pagination for more than 50 results)
def search_restaurants(location, term, limit=50, offset=0):
    search_url = f"https://api.yelp.com/v3/businesses/search?location={location}&term={term}&limit={limit}&offset={offset}"
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json().get('businesses', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching businesses: {e}")
        return []

# Step 2: Get a limited number of reviews (1 review per restaurant)
def get_reviews(business_id):
    reviews_url = f"https://api.yelp.com/v3/businesses/{business_id}/reviews?limit={max_reviews_per_restaurant}"
    try:
        response = requests.get(reviews_url, headers=headers)
        response.raise_for_status()
        return response.json().get('reviews', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews for {business_id}: {e}")
        return []

# Step 3: Fetch all businesses and reviews (up to max_results)
def fetch_business_reviews(location, term, max_results=100):
    all_reviews = []
    seen_business_ids = set()  # Set to track already seen business IDs
    
    # Calculate the total number of pages needed to fetch max_results
    pages_needed = (max_results // 50) + (1 if max_results % 50 != 0 else 0)
    
    for page in range(pages_needed):
        offset = page * 50
        businesses = search_restaurants(location, term, limit=50, offset=offset)
        
        if not businesses:
            continue  # If no businesses found, skip to the next page
        
        for business in businesses:
            business_id = business['id']
            
            # Skip if the business has already been processed
            if business_id in seen_business_ids:
                continue
            
            seen_business_ids.add(business_id)
            
            print(f"\nFetching reviews for {business['name']} (ID: {business_id})...")
            
            # Fetch 1 review for each business
            reviews = get_reviews(business_id)

            if reviews:
                all_reviews.append({
                    'business_name': business['name'],
                    'review_text': reviews[0]['text']  # Only store the review text
                })

            # Sleep to avoid hitting the rate limit
            time.sleep(random.uniform(1, 3))  # Sleep for a random period between 1-3 seconds
    
    return all_reviews

# Step 4: Write the results to a CSV file in the same directory as the script
def write_to_csv(reviews, filename="restaurants_reviews.csv"):
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    
    # Join the directory with the desired filename
    file_path = os.path.join(script_dir, filename)
    
    # Specify the CSV fieldnames (columns)
    fieldnames = ['business_name', 'review_text']
    
    # Open a new CSV file for writing
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Write the header row
        writer.writeheader()
        
        # Write the reviews
        for review_data in reviews:
            writer.writerow({
                'business_name': review_data['business_name'],
                'review_text': review_data['review_text']
            })
    
    print(f"Reviews saved to {file_path}")

# Run the function to get businesses and their reviews
reviews = fetch_business_reviews(location, term, max_results)

# Write the results to a CSV file in the same directory as the script
write_to_csv(reviews)
