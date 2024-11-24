import asyncio
import aiohttp
import csv
import os
from typing import List, Dict

api_keys = ["NZQG3fuTbnmManKnYgq2LOXkYedSHOBzwCfODVCS0XXiUxXQQ1rCI0VPRc5o9mXwvhQrDPsJnu2AyVhG52C-Za2g44OUiFWYwDsB2UntwhM4rhoQdgDIWzoHhVVDZ3Yx", "qDhtGGUl6f8kENMzN0qCIaoDuNjO6xhagyBMFnom2Wp2RL-Ps9Yn5M5Tw3U52q2tQyf8gHKJbV61fRtvUui0DBcFkE7RVujUgnxdXurSdQB5XypW44lr03qKSqBCZ3Yx"]
api_key_index = 0

async def fetch_reviews(session, headers, business_ids: List[str], reviews_per_restaurant: int):
    reviews = []
    for business_id in business_ids:
        review_url = f"https://api.yelp.com/v3/businesses/{business_id}/reviews"
        async with session.get(review_url, headers=headers) as response:
            if response.status != 200:
                reviews.append([])  
            else:
                data = await response.json()
                reviews.append(data.get('reviews', [])[:reviews_per_restaurant])  
    return reviews

async def fetch_restaurants_with_reviews(
    location: str,
    reviews_per_restaurant: int = 3,
    total_restaurants: int = 458
) -> List[Dict]:
    global api_key_index
    headers = {
        "Authorization": f"Bearer {api_keys[api_key_index]}",
        "Accept": "application/json"
    }
    search_url = "https://api.yelp.com/v3/businesses/search"
    restaurants = []
    limit_per_request = 50  

    async with aiohttp.ClientSession() as session:
        for offset in range(0, total_restaurants, limit_per_request):
            params = {
                "location": location,
                "term": "restaurant",
                "limit": limit_per_request,
                "offset": offset
            }
            
            if offset % 100 == 0 and offset != 0:
                api_key_index = (api_key_index + 1) % len(api_keys)
                headers["Authorization"] = f"Bearer {api_keys[api_key_index]}"
                
            async with session.get(search_url, headers=headers, params=params) as response:
                if response.status != 200:
                    continue
                data = await response.json()
                fetched_restaurants = data.get('businesses', [])
                if not fetched_restaurants:
                    break  
                restaurants.extend(fetched_restaurants)
        
        business_ids = [restaurant['id'] for restaurant in restaurants]
        
        reviews = await fetch_reviews(session, headers, business_ids, reviews_per_restaurant)
        
        restaurants_with_reviews = []
        for restaurant, review_set in zip(restaurants, reviews):
            restaurant_data = {
                'business_name': restaurant['name'],
                'reviews': review_set  
            }
            restaurants_with_reviews.append(restaurant_data)
        
        print(f"Fetched {len(restaurants_with_reviews)} restaurants with reviews.")  # Debugging line
        return restaurants_with_reviews

def save_to_csv(data, filename="restaurants_reviews.csv"):
    if not data:
        print("No data to save.")  # Debugging line
        return
    
    current_directory = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(current_directory, filename)
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Business Name", "Review Text"])

        for restaurant in data:
            if not restaurant['reviews']:  # Debugging line to check if there are reviews
                print(f"No reviews for {restaurant['business_name']}.")
            for review in restaurant['reviews']:
                writer.writerow([restaurant['business_name'], review.get('text', 'No text')])

    print(f"Data saved to '{file_path}'")

def main():
    location = "10003"  

    results = asyncio.run(
        fetch_restaurants_with_reviews(
            location=location,
        )
    )

    if not results:
        print("No results fetched.")  # Debugging line

    save_to_csv(results)

if __name__ == "__main__":
    main()
