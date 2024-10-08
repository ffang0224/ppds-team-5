import csv
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Initialize Firebase app (you need to replace 'firebase_credentials.json' with your actual service account key file)
cred = credentials.Certificate('firebase_credentials.json')
firebase_admin.initialize_app(cred)

# Get a Firestore client
db = firestore.client()

# Parse JSON if string (source: https://stackoverflow.com/questions/152580/whats-the-canonical-way-to-check-for-type-in-python)
def parse_json_field(field):
    if isinstance(field, str):
        try:
            return json.loads(field)
        except json.JSONDecodeError:
            return field
    return field

# Parse Boolean
def parse_boolean(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() == 'true'


# Custom JSON input depending on the type. Reviews, multiitem lists (such as tags) and hours have different fields required.
def get_json_input(field_name, is_list=False, is_hours=False, is_review=False):
    if is_list:
        print(f"Enter {field_name} (type 'done' when finished):")
        items = []
        while True:
            item = input("> ")
            if item.lower() == 'done':
                break
            items.append(item)
        return items
    
    elif is_hours:
        print(f"Enter {field_name}:")
        result = {}
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            print(f"Enter hours for {day.capitalize()}:")
            open_time = input(" Open time (e.g., 09:00): ")
            close_time = input(" Close time (e.g., 22:00): ")
            result[day] = {"open": open_time, "close": close_time}
        return result
    
    elif is_review:
        print(f"Enter {field_name}:")
        reviews = []
        while True:
            review = {}
            review['commentAuthor'] = input("Enter comment author (or 'done' to finish): ")
            if review['commentAuthor'].lower() == 'done':
                break
            review['review'] = input("Enter review: ")
            if 'maps' in field_name.lower():
                review['stars'] = float(input("Enter stars (1-5): "))
            if 'reddit' in field_name.lower():
                review['restaurantImage'] = input("Enter restaurant image URL: ")
                review['summary'] = input("Enter summary: ")
            reviews.append(review)
        return reviews
    
    # Normal input for cases outside of those
    else:
        print(f"Enter {field_name}:")
        result = {}
        while True:
            key = input("Enter key (or 'done' to finish): ")
            if key.lower() == 'done':
                break
            value = input(f"Enter value for {key}: ")
            result[key] = value
        return result


# Get booleans (halal, vegetarian, etc)
def get_boolean_input(field_name):
    while True:
        value = input(f"Enter {field_name} (true/false): ").lower()
        if value in ['true', 'false']:
            return value == 'true'
        print("Invalid input. Please enter 'true' or 'false'.")

# Number input (review stars, etc)
def get_number_input(field_name):
    while True:
        try:
            return float(input(f"Enter {field_name}: "))
        except ValueError:
            print("Invalid input. Please enter a number.")

# Check for invalid/missing fields to sanitize database.
def validate_restaurant_data(restaurant_data):
    # Validate required fields
    required_fields = ['restaurantId', 'name', 'address', 'city', 'state', 'country']
    for field in required_fields:
        if not restaurant_data.get(field):
            raise ValueError(f"Missing required field: {field}")
    
    # Validate numeric fields
    numeric_fields = ['latitude', 'longitude', 'averageRating', 'totalReviews']
    for field in numeric_fields:
        if field in restaurant_data:
            try:
                restaurant_data[field] = float(restaurant_data[field])
            except ValueError:
                raise ValueError(f"Invalid numeric value for {field}")
    
    # Validate latitude and longitude
    if 'latitude' in restaurant_data and 'longitude' in restaurant_data:
        lat, lon = restaurant_data['latitude'], restaurant_data['longitude']
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError("Invalid latitude or longitude value")
    
    # Validate JSON fields
    json_fields = ['cuisines', 'hours', 'images', 'tags', 'popularDishes', 'specialties', 
                   'instagramReviews', 'mapsReviews', 'redditReviews']
    for field in json_fields:
        if field in restaurant_data:
            restaurant_data[field] = parse_json_field(restaurant_data[field])
    
    return restaurant_data


# ----------------------------------------------------------------------------
# RESTAURANT OPERATIONS


def add_restaurant_to_firestore(restaurant_data, collection_name):
    restaurant_data = validate_restaurant_data(restaurant_data)
    
    # Parse boolean fields
    boolean_fields = ['takeout', 'delivery', 'dineIn', 'outdoorSeating', 'wifi', 'vegetarian', 'vegan', 'glutenFree', 'halal', 'kosher']
    for field in boolean_fields:
        if field in restaurant_data:
            restaurant_data[field] = parse_boolean(restaurant_data[field])
    
    # Create nested objects
    restaurant_data['location'] = {
        'address': restaurant_data.pop('address'),
        'city': restaurant_data.pop('city'),
        'state': restaurant_data.pop('state'),
        'country': restaurant_data.pop('country'),
        'postalCode': restaurant_data.pop('postalCode', None),
        'coordinates': firestore.GeoPoint(restaurant_data.pop('latitude'), restaurant_data.pop('longitude'))
    }
    
    restaurant_data['contact'] = {
        'phone': restaurant_data.pop('phone', None),
        'email': restaurant_data.pop('email', None),
        'website': restaurant_data.pop('website', None)
    }
    
    restaurant_data['features'] = {
        'takeout': restaurant_data.pop('takeout', False),
        'delivery': restaurant_data.pop('delivery', False),
        'dineIn': restaurant_data.pop('dineIn', False),
        'outdoorSeating': restaurant_data.pop('outdoorSeating', False),
        'wifi': restaurant_data.pop('wifi', False),
        'parking': restaurant_data.pop('parking', None)
    }
    
    restaurant_data['dietaryOptions'] = {
        'vegetarian': restaurant_data.pop('vegetarian', False),
        'vegan': restaurant_data.pop('vegan', False),
        'glutenFree': restaurant_data.pop('glutenFree', False),
        'halal': restaurant_data.pop('halal', False),
        'kosher': restaurant_data.pop('kosher', False)
    }

    # Use the restaurantId as the document ID
    doc_ref = db.collection(collection_name).document(restaurant_data['restaurantId'])
    doc_ref.set(restaurant_data)
    print(f"Restaurant added to collection {collection_name} with ID: {restaurant_data['restaurantId']}")

def update_restaurant(restaurant_id, updated_data, collection_name):
    updated_data = validate_restaurant_data(updated_data)
    doc_ref = db.collection(collection_name).document(restaurant_id)
    doc_ref.update(updated_data)
    print(f"Restaurant with ID {restaurant_id} updated successfully.")

def delete_restaurant(restaurant_id, collection_name):
    db.collection(collection_name).document(restaurant_id).delete()
    print(f"Restaurant with ID {restaurant_id} deleted successfully.")

def read_restaurant(restaurant_id, collection_name):
    doc = db.collection(collection_name).document(restaurant_id).get()
    if doc.exists:
        print(f"Restaurant data: {doc.to_dict()}")
    else:
        print(f"No restaurant found with ID {restaurant_id}")



# ----------------------------------------------------------------------------
# PLAYLIST OPERATIONS


def add_playlist_to_firestore(playlist_data, playlist_collection_name, restaurant_collection_name):
    # Parse JSON fields
    playlist_data['restaurants'] = parse_json_field(playlist_data['restaurants'])
    
    # Create a list of document references for the restaurants
    restaurant_refs = []
    for restaurant in playlist_data['restaurants']:
        restaurant_ref = db.collection(restaurant_collection_name).document(restaurant['restaurantId'])
        restaurant_refs.append(restaurant_ref)
    
    # Replace the restaurant list with document references
    playlist_data['restaurants'] = restaurant_refs
    
    # Add a new doc with an auto-generated ID
    doc_ref = db.collection(playlist_collection_name).document()
    doc_ref.set(playlist_data)
    print(f"Playlist added to collection {playlist_collection_name} with ID: {doc_ref.id}")
    
    return doc_ref.id

def update_playlist(playlist_id, updated_data, playlist_collection_name, restaurant_collection_name):
    if 'restaurants' in updated_data:
        updated_data['restaurants'] = parse_json_field(updated_data['restaurants'])
        restaurant_refs = []
        for restaurant in updated_data['restaurants']:
            restaurant_ref = db.collection(restaurant_collection_name).document(restaurant['restaurantId'])
            restaurant_refs.append(restaurant_ref)
        updated_data['restaurants'] = restaurant_refs

    doc_ref = db.collection(playlist_collection_name).document(playlist_id)
    doc_ref.update(updated_data)
    print(f"Playlist with ID {playlist_id} updated successfully.")

def delete_playlist(playlist_id, collection_name):
    db.collection(collection_name).document(playlist_id).delete()
    print(f"Playlist with ID {playlist_id} deleted successfully.")

def read_playlist(playlist_id, collection_name):
    doc = db.collection(collection_name).document(playlist_id).get()
    if doc.exists:
        print(f"Playlist data: {doc.to_dict()}")
    else:
        print(f"No playlist found with ID {playlist_id}")



# ----------------------------------------------------------------------------
# USER OPERATIONS


def add_user_to_firestore(user_data, user_collection_name, playlist_collection_name):
    # Parse JSON fields
    user_data['playlists'] = parse_json_field(user_data['playlists'])
    user_data['points'] = parse_json_field(user_data['points'])
    
    # Create a list of document references for the playlists
    playlist_refs = []
    for playlist in user_data['playlists']:
        playlist_ref = db.collection(playlist_collection_name).document(playlist['playlistId'])
        playlist_refs.append(playlist_ref)
    
    # Replace the playlist list with document references
    user_data['playlists'] = playlist_refs
    
    # Add a new doc with the username as the document ID
    doc_ref = db.collection(user_collection_name).document(user_data['username'])
    doc_ref.set(user_data)
    print(f"User added to collection {user_collection_name} with username: {user_data['username']}")

def update_user(username, updated_data, user_collection_name, playlist_collection_name):
    if 'playlists' in updated_data:
        updated_data['playlists'] = parse_json_field(updated_data['playlists'])
        playlist_refs = []
        for playlist in updated_data['playlists']:
            playlist_ref = db.collection(playlist_collection_name).document(playlist['playlistId'])
            playlist_refs.append(playlist_ref)
        updated_data['playlists'] = playlist_refs

    if 'points' in updated_data:
        updated_data['points'] = parse_json_field(updated_data['points'])

    doc_ref = db.collection(user_collection_name).document(username)
    doc_ref.update(updated_data)
    print(f"User with username {username} updated successfully.")

def delete_user(username, collection_name):
    db.collection(collection_name).document(username).delete()
    print(f"User with username {username} deleted successfully.")

def read_user(username, collection_name):
    doc = db.collection(collection_name).document(username).get()
    if doc.exists:
        print(f"User data: {doc.to_dict()}")
    else:
        print(f"No user found with username {username}")


# Manual input functions


def add_restaurant_manual():
    print("\nAdding a new restaurant manually:")
    restaurant_data = {}
    
    # String fields
    string_fields = ['restaurantId', 'name', 'address', 'city', 'state', 'country', 'postalCode', 
                     'phone', 'email', 'website', 'priceRange', 'reservationLink']
    for field in string_fields:
        restaurant_data[field] = input(f"Enter {field}: ")
    
    # JSON fields
    restaurant_data['cuisines'] = get_json_input('cuisines', is_list=True)
    restaurant_data['hours'] = get_json_input('hours', is_hours=True)
    restaurant_data['images'] = get_json_input('images', is_list=True)
    restaurant_data['tags'] = get_json_input('tags', is_list=True)
    restaurant_data['popularDishes'] = get_json_input('popular dishes', is_list=True)
    restaurant_data['specialties'] = get_json_input('specialties', is_list=True)
    
    # Review fields
    restaurant_data['instagramReviews'] = get_json_input('Instagram reviews', is_review=True)
    restaurant_data['mapsReviews'] = get_json_input('Maps reviews', is_review=True)
    restaurant_data['redditReviews'] = get_json_input('Reddit reviews', is_review=True)
    
    # Boolean fields
    boolean_fields = ['takeout', 'delivery', 'dineIn', 'outdoorSeating', 'wifi', 'parking', 
                      'vegetarian', 'vegan', 'glutenFree', 'halal', 'kosher']
    for field in boolean_fields:
        restaurant_data[field] = get_boolean_input(field)
    
    # Number fields
    number_fields = ['latitude', 'longitude', 'averageRating', 'totalReviews']
    for field in number_fields:
        restaurant_data[field] = get_number_input(field)
    
    add_restaurant_to_firestore(restaurant_data, RESTAURANT_COLLECTION)

def add_playlist_manual():
    print("\nAdding a new playlist manually:")
    playlist_data = {}
    playlist_data['username'] = input("Enter username: ")
    playlist_data['author'] = input("Enter author: ")
    playlist_data['description'] = input("Enter description: ")
    playlist_data['name'] = input("Enter name: ")
    playlist_data['restaurants'] = get_json_input("restaurants (list of restaurant IDs)", is_list=True)
    
    add_playlist_to_firestore(playlist_data, PLAYLIST_COLLECTION, RESTAURANT_COLLECTION)

def add_user_manual():
    print("\nAdding a new user manually:")
    user_data = {}
    user_data['email'] = input("Enter email: ")
    user_data['firstName'] = input("Enter first name: ")
    user_data['lastName'] = input("Enter last name: ")
    user_data['username'] = input("Enter username: ")
    user_data['playlists'] = get_json_input("playlists (list of playlist IDs)", is_list=True)
    
    print("Enter points:")
    user_data['points'] = {
        'generalPoints': int(input("Enter general points: ")),
        'postPoints': int(input("Enter post points: ")),
        'reviewPoints': int(input("Enter review points: "))
    }
    
    add_user_to_firestore(user_data, USER_COLLECTION, PLAYLIST_COLLECTION)



# CSV input functions


def add_restaurant_csv():
    csv_file_path = input("Enter the path to your restaurant CSV file: ")
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            add_restaurant_to_firestore(row, RESTAURANT_COLLECTION)
    print("All restaurants from CSV have been added to Firestore.")

def add_playlist_csv():
    csv_file_path = input("Enter the path to your playlist CSV file: ")
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            add_playlist_to_firestore(row, PLAYLIST_COLLECTION, RESTAURANT_COLLECTION)
    print("All playlists from CSV have been added to Firestore.")

def add_user_csv():
    csv_file_path = input("Enter the path to your user CSV file: ")
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            add_user_to_firestore(row, USER_COLLECTION, PLAYLIST_COLLECTION)
    print("All users from CSV have been added to Firestore.")
    
    
    
# Global variables for collection names
RESTAURANT_COLLECTION = "restaurants"
PLAYLIST_COLLECTION = "playlists"
USER_COLLECTION = "users"

# List all

def list_all_restaurants(collection_name):
    docs = db.collection(collection_name).stream()
    for doc in docs:
        print(f"Restaurant ID: {doc.id}, Data: {doc.to_dict()}\n")

def list_all_playlists(collection_name):
    docs = db.collection(collection_name).stream()
    for doc in docs:
        print(f"Playlist ID: {doc.id}, Data: {doc.to_dict()}\n")

def list_all_users(collection_name):
    docs = db.collection(collection_name).stream()
    for doc in docs:
        print(f"User ID: {doc.id}, Data: {doc.to_dict()}\n")

def print_menu():
    print("\n--- Restaurant, Playlist, and User Manager ---")
    print("1. Add a new restaurant manually")
    print("2. Add restaurants from CSV")
    print("3. Update a restaurant")
    print("4. Delete a restaurant")
    print("5. Read a restaurant")
    print("6. List all restaurants\n")
    print("7. Add a new playlist manually")
    print("8. Add playlists from CSV")
    print("9. Update a playlist")
    print("10. Delete a playlist")
    print("11. Read a playlist")
    print("12. List all playlists\n")
    print("13. Add a new user manually")
    print("14. Add users from CSV")
    print("15. Update a user")
    print("16. Delete a user")
    print("17. Read a user")
    print("18. List all users\n")
    print("19. Exit")

# Main program loop
def main():
    while True:
        print_menu()
        choice = input("Enter your choice (1-19): ")
        
        if choice == '1':
            add_restaurant_manual()
        elif choice == '2':
            add_restaurant_csv()
        elif choice == '3':
            restaurant_id = input("Enter restaurant ID to update: ")
            updated_data = {}
            print("Enter updated data (leave blank to skip):")
            fields = ['name', 'cuisines', 'address', 'city', 'state', 'country', 'postalCode', 'phone', 'email', 'website', 'priceRange', 'reservationLink']
            for field in fields:
                value = input(f"Enter new {field}: ")
                if value:
                    updated_data[field] = value
        
            # Handle JSON fields
            json_fields = ['images', 'tags', 'popularDishes', 'specialties']
            for field in json_fields:
                if input(f"Update {field}? (y/n): ").lower() == 'y':
                    updated_data[field] = get_json_input(field, is_list=(field in ['images', 'tags', 'popularDishes', 'specialties']))
        
            # Handle hours separately
            if input("Update hours? (y/n): ").lower() == 'y':
                updated_data['hours'] = get_json_input('hours', is_hours=True)
        
            # Handle review fields
            review_fields = ['instagramReviews', 'mapsReviews', 'redditReviews']
            for field in review_fields:
                if input(f"Update {field}? (y/n): ").lower() == 'y':
                    updated_data[field] = get_json_input(field, is_review=True)
        
            # Handle boolean fields
            boolean_fields = ['takeout', 'delivery', 'dineIn', 'outdoorSeating', 'wifi', 'parking', 
                          'vegetarian', 'vegan', 'glutenFree', 'halal', 'kosher']
            for field in boolean_fields:
                if input(f"Update {field}? (y/n): ").lower() == 'y':
                    updated_data[field] = get_boolean_input(field)
        
            # Handle number fields
            number_fields = ['latitude', 'longitude', 'averageRating', 'totalReviews']
            for field in number_fields:
                if input(f"Update {field}? (y/n): ").lower() == 'y':
                    updated_data[field] = get_number_input(field)
        
            update_restaurant(restaurant_id, updated_data, RESTAURANT_COLLECTION)
        elif choice == '4':
            restaurant_id = input("Enter restaurant ID to delete: ")
            delete_restaurant(restaurant_id, RESTAURANT_COLLECTION)
        elif choice == '5':
            restaurant_id = input("Enter restaurant ID to read: ")
            read_restaurant(restaurant_id, RESTAURANT_COLLECTION)
        elif choice == '6':
            list_all_restaurants(RESTAURANT_COLLECTION)
        elif choice == '7':
            add_playlist_manual()
        elif choice == '8':
            add_playlist_csv()
        elif choice == '9':
            playlist_id = input("Enter playlist ID to update: ")
            updated_data = {}
            print("Enter updated data (leave blank to skip):")
            for field in ['name', 'description']:
                value = input(f"Enter new {field}: ")
                if value:
                    updated_data[field] = value
            if input("Update restaurants? (y/n): ").lower() == 'y':
                updated_data['restaurants'] = get_json_input("restaurants (list of restaurant IDs)", is_list=True)
            update_playlist(playlist_id, updated_data, PLAYLIST_COLLECTION, RESTAURANT_COLLECTION)
        elif choice == '10':
            playlist_id = input("Enter playlist ID to delete: ")
            delete_playlist(playlist_id, PLAYLIST_COLLECTION)
        elif choice == '11':
            playlist_id = input("Enter playlist ID to read: ")
            read_playlist(playlist_id, PLAYLIST_COLLECTION)
        elif choice == '12':
            list_all_playlists(PLAYLIST_COLLECTION)
        elif choice == '13':
            add_user_manual()
        elif choice == '14':
            add_user_csv()
        elif choice == '15':
            username = input("Enter username to update: ")
            updated_data = {}
            print("Enter updated data (leave blank to skip):")
            for field in ['email', 'firstName', 'lastName']:
                value = input(f"Enter new {field}: ")
                if value:
                    updated_data[field] = value
            if input("Update playlists? (y/n): ").lower() == 'y':
                updated_data['playlists'] = get_json_input("playlists (list of playlist IDs)", is_list=True)
            if input("Update points? (y/n): ").lower() == 'y':
                updated_data['points'] = {
                    'generalPoints': int(input("Enter new general points: ")),
                    'postPoints': int(input("Enter new post points: ")),
                    'reviewPoints': int(input("Enter new review points: "))
                }
            update_user(username, updated_data, USER_COLLECTION, PLAYLIST_COLLECTION)
        elif choice == '16':
            username = input("Enter username to delete: ")
            delete_user(username, USER_COLLECTION)
        elif choice == '17':
            username = input("Enter username to read: ")
            read_user(username, USER_COLLECTION)
        elif choice == '18':
            list_all_users(USER_COLLECTION)
        elif choice == '19':
            print("Exiting the program. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    print("Starting the Restaurant, Playlist, and User Manager...")
    main()