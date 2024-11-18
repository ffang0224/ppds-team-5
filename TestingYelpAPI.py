import requests
import argparse
import pprint

BASE_URL = "https://serpapi.com/search.json"
API_KEY = "58dc2fa4896f10d7ad7154b7b22c876f89baad627dab1bf1f5e110583523c5e9"  #API key is replaced here just for testing
ENGINE_SEARCH = "yelp"
ENGINE_REVIEWS = "yelp_reviews"
DEFAULT_LOCATION = "New York, NY"  

def fetch_place_id(term, location):
    """
    Fetch the Yelp place ID for a given search term and location.

    Args:
        term (str): Search term (restaurant name or keyword).
        location (str): Location of the search.

    Returns:
        str: Yelp place ID or None if not found.
    """
    params = {
        "engine": ENGINE_SEARCH,
        "q": term,
        "find_loc": location,
        "api_key": API_KEY,
    }

    print(f"DEBUG: Querying {BASE_URL} with params: {params}")
    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.json().get('error', 'Unknown error')}")
        return None

    results = response.json().get("organic_results", [])
    if not results:
        print(f"No results found for '{term}' in {location}.")
        return None

    # Attempt to find the best match
    for result in results:
        if term.lower() in result["title"].lower():
            print(f"Found exact match: {result['title']} (ID: {result['place_ids'][0]})")
            return result["place_ids"][0]

    print(f"No exact match found for '{term}' in {location}.")
    return None

def fetch_reviews(place_id):
    """
    Fetch reviews for a given Yelp place ID.

    Args:
        place_id (str): Yelp place ID.

    Returns:
        list: List of the first three reviews.
    """
    params = {
        "engine": ENGINE_REVIEWS,
        "place_id": place_id,
        "api_key": API_KEY,
    }

    print(f"DEBUG: Fetching reviews for place ID: {place_id}")
    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.json().get('error', 'Unknown error')}")
        return None

    reviews = response.json().get("reviews", [])
    if not reviews:
        print(f"No reviews found for place ID: {place_id}.")
        return None

    # Limit to the first three reviews
    return reviews[:3]


def main():
    """
    Main function to parse command-line arguments and fetch reviews.
    """
    parser = argparse.ArgumentParser(description="Fetch Yelp reviews for a restaurant.")
    parser.add_argument("-q", "--term", help="Search term (e.g., restaurant name).")
    parser.add_argument(
        "-l",
        "--location",
        default=DEFAULT_LOCATION,
        help=f"Search location (default: {DEFAULT_LOCATION}).",
    )
    args = parser.parse_args()
    term = args.term or input("Enter the restaurant name or search term: ")
    location = args.location
    place_id = fetch_place_id(term, location)
    if not place_id:
        print("Could not find a matching place.")
        return
    reviews = fetch_reviews(place_id)
    if reviews:
        print(f"\nReviews for {term} in {location}:")
        for idx, review in enumerate(reviews, start=1):
            print(f"\n--- Review {idx} ---")
            print(f"User: {review['user']['name']}")
            print(f"Rating: {review['rating']}")
            print(f"Comment: {review['comment']['text']}")
    else:
        print("No reviews available.")


if __name__ == "__main__":
    main()
