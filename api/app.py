from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any, TypeVar
from datetime import datetime
import firebase_admin
import json
from firebase_admin import credentials, firestore
from google.cloud import firestore as gc_firestore
from google.cloud.firestore import GeoPoint
import aiofiles
import os
from typing import Optional
import requests
from math import radians, sin, cos, sqrt, atan2, ceil


def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

# Call the function before accessing environment variables
load_env_file()

# Initialize Firebase app
cred = credentials.Certificate(json.loads(os.environ['FIREBASE_CREDENTIALS']))
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

T = TypeVar('T')

def convert_to_json_serializable(data: Any) -> Any:
    """
    Convert Firestore data types to JSON serializable formats.
    Handles nested dictionaries, lists, GeoPoints, DocumentReferences, 
    DocumentSnapshots, and datetime objects.
    """
    try:
        if data is None:
            return None
            
        # Handle datetime
        if isinstance(data, datetime):
            return data.isoformat()
            
        # Handle Firestore document references and snapshots
        if isinstance(data, (firestore.DocumentReference, firestore.DocumentSnapshot)):
            return str(data.path)
            
        # Handle GeoPoint
        if isinstance(data, GeoPoint):
            return {
                'lat': data.latitude,
                'lng': data.longitude
            }
            
        # Handle dictionaries (including DocumentSnapshot conversion)
        if isinstance(data, dict) or hasattr(data, 'to_dict'):
            # Convert DocumentSnapshot to dict if needed
            source_dict = data.to_dict() if hasattr(data, 'to_dict') else data
            return {k: convert_to_json_serializable(v) for k, v in source_dict.items()}
            
        # Handle lists
        if isinstance(data, list):
            return [convert_to_json_serializable(i) for i in data]
            
        return data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data serialization error: {str(e)}"
        )

# Main validation and serialization function to use in endpoints
def validate_and_serialize(data: Any) -> dict:
    """
    Main function to validate and serialize Firestore data.
    Use this function in your endpoints to process Firestore data.
    """
    return convert_to_json_serializable(data)

# Convert Firestore GeoPoint to dict
def convert_geopoint(geopoint):
    if isinstance(geopoint, GeoPoint):
        return {
            "lat": geopoint.latitude,
            "lng": geopoint.longitude
        }
    return geopoint

# Convert datetime to ISO string
def convert_datetime(dt):
    if hasattr(dt, 'timestamp'):
        return dt.isoformat()
    return dt

# Models!
class Points(BaseModel):
    generalPoints: int = 0
    postPoints: int = 0
    reviewPoints: int = 0

class UserBase(BaseModel):
    email: str
    firstName: str
    lastName: str
    username: str
    uid: str
    points: Points = Field(default_factory=Points)
    playlists: List[str] = Field(default_factory=list)
    lists: List[str] = Field(default_factory=list)  # Added for restaurant lists
    emailVerified: bool = False
    numOfLists: int = 0

class UserUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    pass
class PointsUpdateRequest(BaseModel):
    points: int = Field(..., description="Number of points to add")
class UserRead(UserBase):
    createdAt: str

# Updated Restaurant Models
class Location(BaseModel):
    lat: float
    lng: float
    address: str

class Restaurant(BaseModel):
    place_id: str
    name: str
    rating: float
    user_ratings_total: int
    address: str
    location: Location
    price_level: Optional[int] = None
    types: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
#review models
class ReviewAuthor(BaseModel):
    name: Optional[str] = None
    profile_photo_url: Optional[str] = None

class Review(BaseModel):
    text: Optional[str] = None
    time: Optional[str] = None
    rating: Optional[int] = None
    author: Optional[Union[str, ReviewAuthor]] = None
    platform: Optional[str] = None
    language: Optional[str] = None

class RestaurantReviews(BaseModel):
    google_place_id: str
    gmaps_name: str
    yelp_name: Optional[str] = None
    yelp_business_id: Optional[str] = None
    fetch_time: str
    reviews: List[Review]

#List model
class RestaurantListBase(BaseModel):
    name: str
    description: Optional[str] = ""
    restaurants: List[str] = Field(default_factory=list)  # List of place_ids
    color: str = "#f97316"
    author: str
    username: str

class RestaurantListRead(RestaurantListBase):
    id: str
    createdAt: Optional[str] = None
    num_likes: int = 0
    favorited_by: List[str] = []

# --- Original User Endpoints ---
@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    try:
        uid_query = db.collection("users").where("uid", "==", user.uid).get()
        if len(list(uid_query)) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this authentication already exists"
            )

        user_doc = db.collection("users").document(user.username).get()
        if user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken"
            )

        user_data = {
            **jsonable_encoder(user),
            "createdAt": datetime.utcnow().isoformat(),
            "points": {
                "generalPoints": 0,
                "postPoints": 0,
                "reviewPoints": 0
            },
            "playlists": [],
            "lists": [],
            "achievements": user.achievements if hasattr(user, 'achievements') else [],
            "numOfLists": 0,
        }

        db.collection("users").document(user.username).set(user_data)

        # Grant "first_account_creation" achievement
        new_achievements = await check_and_award_achievements(user.username, "first_account_creation")

        return {
            "message": "User created successfully",
            "username": user.username,
            "newAchievements": new_achievements,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get("/users/{username}", response_model=UserRead)
async def get_user(username: str):
    try:
        user_doc = db.collection("users").document(username).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        user_data = user_doc.to_dict()
        serialized_data = convert_to_json_serializable(user_data)
        
        return serialized_data

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/users/{username}/updatePoints", response_model=dict)
async def update_user_points(
    username: str,
    points_update: PointsUpdateRequest,
):
    try:
        # Get user reference
        users_ref = db.collection('users')
        user_query = users_ref.where('username', '==', username).limit(1)
        user_docs = user_query.stream()
        
        # Get the user document
        user_doc = next(user_docs, None)
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {username} not found"
            )
            
        # Get current points
        current_points = user_doc.get('points', {})
        if not isinstance(current_points, dict):
            current_points = {
                'generalPoints': 0,
                'postPoints': 0,
                'reviewPoints': 0
            }
            
        # Update general points only
        new_general_points = current_points.get('generalPoints', 0) + points_update.points
        
        # Update only the generalPoints
        user_doc.reference.update({
            'points.generalPoints': new_general_points
        })
        
        return {
            "success": True,
            "message": f"Successfully updated points for user {username}",
            "newPoints": {
                'generalPoints': new_general_points
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update points: {str(e)}"
        )

@app.post("/users/{user_id}")
async def update_user(user_id: str, user_update: UserUpdateRequest):
    try:
        
        # Get reference to user document
        user_ref = db.collection("users").document(user_id)
        
        # Prepare update data (remove None values)
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid update data provided"
            )
        
        # Add updated timestamp
        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        # Update the document
        user_ref.update(update_data)
        
        # Get and return the updated document
        updated_doc = user_ref.get()
        return updated_doc.to_dict()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/auth/{uid}", response_model=UserRead)
async def get_user_by_uid(uid: str):
    try:
        users = db.collection("users").where("uid", "==", uid).limit(1).get()
        user_list = list(users)
        
        if not user_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with UID '{uid}' not found"
            )

        user_data = user_list[0].to_dict()
        serialized_data = convert_to_json_serializable(user_data)
        
        return serialized_data

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error getting user by UID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/users/auth/{uid}", response_model=UserRead)
async def update_user_by_uid(uid: str, user_update: UserUpdateRequest):
    try:
        # Fetch the user data from Firestore
        users = db.collection("users").where("uid", "==", uid).limit(1).get()
        user_list = list(users)
        
        if not user_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with UID '{uid}' not found"
            )
        
        # Get the user document reference
        user_ref = user_list[0].reference
        
        # Prepare update data (only include fields that are provided)
        update_data = {}
        if user_update.firstName is not None:
            update_data["firstName"] = user_update.firstName
        if user_update.lastName is not None:
            update_data["lastName"] = user_update.lastName
        if user_update.email is not None:
            update_data["email"] = user_update.email
        if user_update.username is not None:
            update_data["username"] = user_update.username
            
        # If no fields to update, raise an error
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided to update"
            )
            
        # Update the user document
        user_ref.update(update_data)
        
        # Fetch and return the updated user data
        updated_user = user_ref.get()
        user_data = updated_user.to_dict()
        return user_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating user by UID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
# Get all users endpoint
@app.get("/users")
async def get_all_users():
    try:
        users_ref = db.collection("users").stream()
        users = []
        for doc in users_ref:
            user_data = doc.to_dict()
            user_data["username"] = doc.id
            users.append(validate_and_serialize(user_data))
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
# Get user's lists with restaurant details
@app.get("/users/{username}/lists/details")
async def get_user_lists_with_details(username: str):
    try:
        lists = await get_user_restaurant_lists(username)
        detailed_lists = []

        for list_item in lists:
            restaurants = []
            for place_id in list_item.get("restaurants", []):
                try:
                    restaurant = await get_restaurant(place_id)
                    restaurants.append(restaurant)
                except:
                    continue

            list_item["detailed_restaurants"] = restaurants
            detailed_lists.append(list_item)

        return detailed_lists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/users/{username}/lists", response_model=List[RestaurantListRead])
async def get_user_lists(username: str):
    try:
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        lists = db.collection("users").document(username).collection("lists").get()
        return [validate_and_serialize(doc.to_dict()) for doc in lists]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/lists/{list_id}", response_model=RestaurantListRead)
async def get_playlist(username: str, list_id: str):
    try:
        doc = db.collection("users").document(username).collection("lists").document(list_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        return validate_and_serialize(doc.to_dict())
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/users/{username}/lists/{list_id}")
async def update_playlist(username: str, list_id: str, playlist: RestaurantListBase):
    try:
        playlist_ref = db.collection("users").document(username).collection("lists").document(list_id)
        if not playlist_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        playlist_ref.update(playlist.dict())
        return {"message": "Playlist updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/users/{username}/lists/{list_id}/restaurants/add")
async def add_place_to_restaurants(username: str, list_id: str, body: dict):
    try:
        place_id = body.get("place_id")
        if not place_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Place ID is required."
            )

        # Get references to both collections
        user_list_ref = db.collection("users").document(username).collection("lists").document(list_id)
        global_list_ref = db.collection("allLists").document(list_id)

        # Verify list exists in user's collection
        user_list_doc = user_list_ref.get()
        if not user_list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"List '{list_id}' not found for user '{username}'."
            )

        # Use batch to update both collections
        batch = db.batch()

        # Update user's list
        batch.update(user_list_ref, {
            "restaurants": firestore.ArrayUnion([place_id])
        })

        # Update global list
        batch.update(global_list_ref, {
            "restaurants": firestore.ArrayUnion([place_id])
        })

        # Commit the batch
        batch.commit()

        return {
            "message": f"Place ID '{place_id}' successfully added to the list '{list_id}'."
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
@app.post("/admin/refresh-restaurant-cache")
async def refresh_restaurant_cache(background_tasks: BackgroundTasks):

    async def update_cache():
        try:
            restaurants_ref = db.collection("restaurants").stream()
            restaurant_list = []

            for doc in restaurants_ref:
                data = doc.to_dict()

                # Collecting data for one restaurant
                restaurant_data = {
                    "name": data.get("name", {}),
                    "ratings": data.get("ratings", {}),
                    "location": data.get("location", {}),
                    "price_level": data.get("price_level", {}),
                    "types": data.get("types", {}),
                    "additional_info": data.get("additional_info", {}),
                    "match_confidence": data.get("match_confidence", None),
                }

                # Append the restaurant data
                restaurant_list.append(restaurant_data)

            # Write the data to the cache file
            async with aiofiles.open('restaurant_cache.json', 'w') as f:
                await f.write(json.dumps(restaurant_list))

            print("Cache updated successfully.")

        except Exception as e:
            print(f"Error updating cache: {str(e)}")

    # Run the update process in the background
    background_tasks.add_task(update_cache)
    return {"message": "Cache refresh started"}

@app.get("/restaurants", response_model=List[dict])
async def get_restaurants(
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    price_level: Optional[int] = None,
):
    """
    Retrieve all restaurants from the cache and apply optional filters:
    - `search`: Search by name (gmaps or yelp).
    - `cuisine`: Filter by types (gmaps or yelp).
    - `price_level`: Filter by price levels (composite).
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('restaurant_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache file not found. Please refresh the cache."
            )

        # Load the cache
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)  # List of restaurants

        # Filter by search
        if search:
            search_lower = search.lower()
            restaurants = [
                r for r in restaurants
                if search_lower in r['name']['gmaps'].lower() or
                   search_lower in r['name']['yelp'].lower()
            ]

        # Filter by cuisine
        if cuisine:
            cuisine_lower = cuisine.lower()
            restaurants = [
                r for r in restaurants
                if cuisine_lower in r['types']['gmaps'] or cuisine_lower in r['types']['yelp']
            ]

        # Filter by price level
        if price_level is not None:
            restaurants = [
                r for r in restaurants
                if r['price_level']['composite']['min'] is not None and
                   r['price_level']['composite']['min'] <= price_level <=
                   r['price_level']['composite']['max']
            ]

        # Return the filtered restaurants
        return restaurants

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving restaurants: {str(e)}"
        )

# Fallback function for when cache fails
async def get_restaurants_from_firestore():
    restaurants = db.collection("restaurants").get()
    return [validate_and_serialize(doc.to_dict()) for doc in restaurants]

@app.get("/restaurants/search", response_model=List[dict])
async def search_restaurants(
    query: Optional[str] = None,
    cuisine: Optional[str] = None,
    price_level: Optional[int] = None
):
    """
    Search for restaurants in the cache based on:
    - `query`: Keywords in name (gmaps or yelp).
    - `cuisine`: Matches types in gmaps or yelp.
    - `price_level`: Matches normalized price levels.
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('restaurant_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache file not found. Please refresh the cache."
            )

        # Load the cache
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)

        # Start with all restaurants
        filtered_restaurants = restaurants

        # Filter by query in names
        if query:
            query_lower = query.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if query_lower in r["name"]["gmaps"].lower() or query_lower in r["name"]["yelp"].lower()
            ]

        # Filter by cuisine
        if cuisine:
            cuisine_lower = cuisine.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if cuisine_lower in r["types"]["gmaps"] or cuisine_lower in r["types"]["yelp"]
            ]

        # Filter by price level
        if price_level is not None:
            filtered_restaurants = [
                r for r in filtered_restaurants
                if r["price_level"]["composite"]["min"] is not None and
                   r["price_level"]["composite"]["min"] <= price_level <=
                   r["price_level"]["composite"]["max"]
            ]

        return filtered_restaurants

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search restaurants: {str(e)}"
        )

@app.get("/restaurants/popular", response_model=List[dict])
async def get_popular_restaurants(limit: int = 10):
    """
    Retrieve the most popular restaurants sorted by:
    - Highest rating (`rating`).
    - Most reviews (`user_ratings_total`) as a tiebreaker.
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('restaurant_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache file not found. Please refresh the cache."
            )

        # Load the cache
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)

        # Sort restaurants by rating (descending) and then by total ratings (descending)
        sorted_restaurants = sorted(
            restaurants,
            key=lambda r: (
                r["ratings"]["gmaps"]["rating"],  # Primary: gmaps rating
                r["ratings"]["gmaps"]["total_ratings"],  # Secondary: gmaps total ratings
            ),
            reverse=True
        )

        # Limit the results
        return sorted_restaurants[:limit]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve popular restaurants: {str(e)}"
        )

@app.get("/restaurants/nearby")
async def get_nearby_restaurants(lat: float, lng: float, radius_km: float = 2.0):
    """
    Retrieve restaurants within a given radius (in kilometers) of a specific location.
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('restaurant_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache file not found. Please refresh the cache."
            )

        # Load cached data
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)

        def haversine_distance(lat1, lng1, lat2, lng2):
            """
            Calculate the great-circle distance between two points on Earth.
            """
            # Convert latitude and longitude from degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            earth_radius_km = 6371  # Radius of Earth in kilometers
            return earth_radius_km * c

        # Filter restaurants within the radius
        nearby = []
        for restaurant in restaurants:
            location = restaurant.get("location", {}).get("gmaps", {})
            r_lat = location.get("lat")
            r_lng = location.get("lng")

            # Skip if location data is missing
            if r_lat is None or r_lng is None:
                continue

            # Calculate the distance using Haversine formula
            distance = haversine_distance(lat, lng, r_lat, r_lng)
            if distance <= radius_km:
                nearby.append(restaurant)

        return nearby

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve nearby restaurants: {str(e)}"
        )

@app.get("/restaurants/{place_id}")
async def get_restaurant(place_id: str):
    """
    Retrieve a single restaurant's full details from the cache by `place_id`.
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('restaurant_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cache file not found. Please refresh the cache."
            )

        # Load the cache
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)

        # Find the restaurant by `place_id`
        restaurant = next(
            (r for r in restaurants if r["additional_info"]["gmaps"]["place_id"] == place_id), None
        )

        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant with place_id {place_id} not found"
            )

        # Return the restaurant data exactly as it exists in the database
        return restaurant

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve restaurant: {str(e)}"
        )

# --- New Restaurant List Endpoints ---

#allLists endpoints
@app.post("/allLists", status_code=status.HTTP_201_CREATED)
async def create_global_restaurant_list(restaurant_list: RestaurantListBase):
    try:
        # Verify the user exists before creating the list
        user_doc = db.collection("users").document(restaurant_list.username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{restaurant_list.username}' not found"
            )

        # Generate new document reference with auto-generated ID
        list_ref = db.collection("allLists").document()

        # Prepare list data with additional global list fields
        list_data = {
            **restaurant_list.dict(),
            "id": list_ref.id,  # Use Firestore's auto-generated ID
            "createdAt": datetime.utcnow().isoformat(),
            "num_likes": 0,
            "favorited_by": [],
        }

        # Set the document in allLists collection
        list_ref.set(list_data)

        return {
            "message": "Global restaurant list created successfully",
            "id": list_ref.id
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 

@app.get("/allLists", response_model=List[RestaurantListRead])
async def get_all_restaurant_lists():
    try:
        # Retrieve all documents from the allLists collection
        lists_ref = db.collection("allLists")
        lists = lists_ref.get()
        
        # Convert Firestore documents to dictionaries and validate
        all_lists = [
            validate_and_serialize(doc.to_dict()) 
            for doc in lists 
            if doc.exists
        ]
        
        # Optional: Sort lists by creation date (most recent first)
        all_lists.sort(
            key=lambda x: x.get('createdAt', ''), 
            reverse=True
        )
        
        return all_lists
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/allLists/paginated", response_model=Dict[str, Any])
async def get_paginated_restaurant_lists(
    page: int = 1, 
    page_size: int = 10,
    sort_by: str = 'createdAt',
    order: str = 'desc'
):
    try:
        lists_ref = db.collection("allLists")
        
        # Apply sorting
        query = lists_ref.order_by(sort_by, direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        offset = (page - 1) * page_size
        lists = query.limit(page_size).offset(offset).get()
        
        # Total count for pagination metadata
        total_count = len(list(lists_ref.get()))
        
        # Convert to list and validate
        paginated_lists = [
            validate_and_serialize(doc.to_dict()) 
            for doc in lists 
            if doc.exists
        ]
        
        return {
            "lists": paginated_lists,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": math.ceil(total_count / page_size)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/allLists/filtered", response_model=List[RestaurantListRead])
async def get_filtered_restaurant_lists(
    username: Optional[str] = None,
    min_likes: Optional[int] = None,
    color: Optional[str] = None
):
    try:
        lists_ref = db.collection("allLists")
        query = lists_ref
        
        # Apply filters
        if username:
            query = query.where('username', '==', username)
        
        if min_likes is not None:
            query = query.where('num_likes', '>=', min_likes)
        
        if color:
            query = query.where('color', '==', color)
        
        lists = query.get()
        
        filtered_lists = [
            validate_and_serialize(doc.to_dict()) 
            for doc in lists 
            if doc.exists
        ]
        
        return filtered_lists
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/allLists/{list_id}", response_model=RestaurantListRead)
async def get_restaurant_list_by_id(list_id: str):
    try:
        # Reference the specific document in allLists collection
        list_ref = db.collection("allLists").document(list_id)
        list_doc = list_ref.get()

        # Check if the document exists
        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant list with ID '{list_id}' not found"
            )

        # Get the list data and validate
        list_data = list_doc.to_dict()
        
        # Optional: Fetch full restaurant details
        full_restaurants = []
        for place_id in list_data.get('restaurants', []):
            try:
                # Fetch full restaurant details from restaurants collection
                restaurant_ref = db.collection("restaurants").document(place_id)
                restaurant_doc = restaurant_ref.get()
                
                if restaurant_doc.exists:
                    full_restaurant = restaurant_doc.to_dict()
                    full_restaurants.append(full_restaurant)
            except Exception as e:
                # Log the error but continue processing
                print(f"Error fetching restaurant {place_id}: {e}")

        # Create a validated response
        validated_list = validate_and_serialize({
            **list_data,
            'full_restaurants': full_restaurants  # Optional: include full restaurant details
        })

        return validated_list

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/allLists/{list_id}/like")
async def like_restaurant_list(
    list_id: str, 
    username: str = Body(...),
    unlike: bool = Body(False, embed=True)
):
    try:
        # Reference the specific list
        list_ref = db.collection("allLists").document(list_id)
        list_doc = list_ref.get()

        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant list with ID '{list_id}' not found"
            )

        # Get current list data
        list_data = list_doc.to_dict()
        favorited_by = list_data.get('favorited_by', [])
        num_likes = list_data.get('num_likes', 0)

        # Update like status
        if unlike and username in favorited_by:
            favorited_by.remove(username)
            num_likes = max(0, num_likes - 1)
        elif not unlike and username not in favorited_by:
            favorited_by.append(username)
            num_likes += 1

        # Update the document
        list_ref.update({
            'favorited_by': favorited_by,
            'num_likes': num_likes
        })

        return {
            "message": "List liked/unliked successfully",
            "num_likes": num_likes,
            "favorited_by": favorited_by
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/allLists/{list_id}")
async def delete_restaurant_list(
    list_id: str, 
    username: str
):
    try:
        # Reference the specific list
        list_ref = db.collection("allLists").document(list_id)
        list_doc = list_ref.get()

        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant list with ID '{list_id}' not found"
            )

        # Check if the user is the author
        list_data = list_doc.to_dict()
        if list_data.get('username') != username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this list"
            )

        # Delete from allLists
        list_ref.delete()

        # Optional: Delete from user's personal lists
        user_list_ref = db.collection("users").document(username).collection("lists").document(list_id)
        user_list_ref.delete()

        return {"message": "List deleted successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/popularLists", response_model=List[RestaurantListRead])
async def get_popular_restaurant_lists():
    try:
        # Retrieve all documents from the allLists collection
        lists_ref = db.collection("allLists")
        lists = lists_ref.get()
        
        # Convert Firestore documents to dictionaries and validate
        all_lists = [
            validate_and_serialize(doc.to_dict()) 
            for doc in lists 
            if doc.exists
        ]
        
        # Sort by 'likes' in descending order and return the top 5
        popular_lists = sorted(
            all_lists, 
            key=lambda x: x.get('likes', 0), 
            reverse=True
        )[:5]
        
        return popular_lists
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/lists/{list_id}/like", status_code=status.HTTP_200_OK)
async def toggle_list_like(list_id: str, data: dict = Body(...)):
    username = data.get('username')
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )
    
    try:
        # Reference to the global list document
        list_ref = db.collection("allLists").document(list_id)
        list_doc = list_ref.get()
        
        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="List not found"
            )
        
        # Get current list data
        list_data = list_doc.to_dict()
        
        # Initialize favorited_by if not exists
        if 'favorited_by' not in list_data:
            list_data['favorited_by'] = []
        
        # Toggle like
        if username in list_data['favorited_by']:
            # Unlike
            list_data['favorited_by'].remove(username)
            list_data['num_likes'] -= 1
            
            # Remove from user's lists
            user_lists_ref = db.collection("users").document(username).collection("lists")
            query = user_lists_ref.where("id", "==", list_id).limit(1)
            liked_list_docs = query.get()
            
            for doc in liked_list_docs:
                doc.reference.delete()
        else:
            # Like
            list_data['favorited_by'].append(username)
            list_data['num_likes'] += 1
            
            # Add to user's lists
            user_lists_ref = db.collection("users").document(username).collection("lists")
            user_lists_ref.add({
                **list_data,
                "is_favorite": True
            })
        
        # Update the document
        list_ref.update({
            'favorited_by': list_data['favorited_by'],
            'num_likes': list_data['num_likes']
        })
        
        return {
            "message": "List like toggled successfully",
            "liked": username in list_data['favorited_by'],
            "num_likes": list_data['num_likes']
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
#users/{username}/lists endpoints
@app.post("/users/{username}/lists", status_code=status.HTTP_201_CREATED)
async def create_restaurant_list(username: str, restaurant_list: RestaurantListBase):
    try:
        # Verify the user exists
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        # Fetch user data
        user_data = user_doc.to_dict()
        current_num_of_lists = user_data.get("numOfLists", 0)
        achievements = user_data.get("achievements", [])

        # Check if this is the user's first list
        is_first_list = current_num_of_lists == 0 and "first_list_created" not in achievements

        # Generate new document reference with auto-generated ID
        user_list_ref = db.collection("users").document(username).collection("lists").document()
        list_id = user_list_ref.id

        # Prepare list data for user and global collections
        list_data = {
            **restaurant_list.dict(),
            "id": list_id,
            "createdAt": datetime.utcnow().isoformat(),
        }
        global_list_data = {
            **list_data,
            "num_likes": 0,
            "favorited_by": [],
        }

        # Use batch writes for atomicity
        batch = db.batch()

        # Add list to user's collection
        batch.set(user_list_ref, list_data)

        # Add list to global collection
        global_list_ref = db.collection("allLists").document(list_id)
        batch.set(global_list_ref, global_list_data)

        # Increment numOfLists for the user
        user_ref = db.collection("users").document(username)
        batch.update(user_ref, {"numOfLists": firestore.Increment(1)})

        # Commit the batch
        batch.commit()

        # Award achievement if it's the user's first list
        new_achievements = []
        if is_first_list:
            new_achievements = await check_and_award_achievements(username, "first_list_created")

        return {
            "message": "Restaurant list created successfully",
            "id": list_id,
            "newAchievements": new_achievements,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error creating restaurant list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    
# @app.get("/users/{username}/lists", response_model=List[RestaurantListRead])
# async def get_user_restaurant_lists(username: str):
#     try:
#         user_doc = db.collection("users").document(username).get()
#         if not user_doc.exists:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"User '{username}' not found"
#             )

#         lists = db.collection("users").document(username).collection("lists").get()
#         return [validate_and_serialize(doc.to_dict()) for doc in lists]
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
@app.get("/users/{username}/lists", response_model=List[RestaurantListRead])
async def get_user_restaurant_lists(username: str):
    try:
        # Verify the user exists
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        # Fetch user's lists
        user_lists = db.collection("users").document(username).collection("lists").get()

        # Fetch corresponding global data from allLists
        user_list_ids = [doc.id for doc in user_lists]
        global_lists_ref = db.collection("allLists")
        global_lists = [
            doc.to_dict()
            for doc in global_lists_ref.where("id", "in", user_list_ids).stream()
        ]

        # Combine data to include global fields
        combined_lists = []
        for user_list_doc in user_lists:
            user_list_data = user_list_doc.to_dict()
            global_data = next(
                (g for g in global_lists if g.get("id") == user_list_data.get("id")), {}
            )
            combined_data = {**user_list_data, **global_data}
            combined_lists.append(validate_and_serialize(combined_data))

        return combined_lists

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/users/{username}/lists/{list_id}")
async def update_restaurant_list(username: str, list_id: str, restaurant_list: RestaurantListBase):
    try:
        list_ref = db.collection("users").document(username).collection("lists").document(list_id)
        if not list_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant list not found"
            )

        # Update list
        list_ref.update(restaurant_list.dict())
        return {"message": "Restaurant list updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
@app.delete("/users/{username}/lists/{list_id}")
async def delete_restaurant_list(username: str, list_id: str):
    try:
        # Get refs
        user_ref = db.collection("users").document(username)
        list_ref = user_ref.collection("lists").document(list_id)
        global_list_ref = db.collection("allLists").document(list_id)

        # Verify list exists and belongs to user
        list_doc = list_ref.get()
        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant list not found"
            )

        # Use batch to delete from both collections
        batch = db.batch()

        # Delete from user's lists collection
        batch.delete(list_ref)

        # Delete from global lists collection
        batch.delete(global_list_ref)

        # Update numOfLists in user's document
        batch.update(user_ref, {
            "numOfLists": firestore.Increment(-1)
        })

        # Commit the batch
        batch.commit()

        return {"message": "Restaurant list deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/users/{username}/lists/{list_id}/restaurants", response_model=List[Restaurant])
async def get_restaurants_in_list(username: str, list_id: str):
    try:
        # Get the list
        list_doc = db.collection("users").document(username)\
                    .collection("lists").document(list_id).get()
        
        if not list_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant list not found"
            )
        
        list_data = list_doc.to_dict()
        place_ids = list_data.get('restaurants', [])
        
        # Get all restaurants in the list using place_id
        restaurants = []
        restaurants_ref = db.collection("restaurants")
        
        for place_id in place_ids:
            query = restaurants_ref.where("place_id", "==", place_id).limit(1)
            docs = query.stream()
            restaurant_doc = next(docs, None)
            
            if restaurant_doc:
                restaurant_data = restaurant_doc.to_dict()
                restaurant_data["id"] = restaurant_doc.id
                restaurants.append(Restaurant(**restaurant_data))
        
        return restaurants   
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

@app.get("/restaurant-photo/{place_id}")
async def get_restaurant_photo(place_id: str):
    try:
        # Get place details from Google Maps API
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "photo",
            "key": GOOGLE_MAPS_API_KEY,
        }
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()

        # Check for errors
        if details_response.status_code != 200 or "error_message" in details_data:
            raise HTTPException(
                status_code=details_response.status_code,
                detail=details_data.get("error_message", "Unknown error occurred."),
            )

        # Get the photo reference
        photo_references = details_data.get("result", {}).get("photos", [])
        if not photo_references:
            return {"photo_url": None}

        # Fetch the photo URL using the first reference
        photo_reference = photo_references[0]["photo_reference"]
        photo_url = (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
        )

        return {"photo_url": photo_url}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch photo: {str(e)}",
        )

@app.get("/restaurant-photos/{place_id}")
async def get_restaurant_photos(place_id: str, limit: int = 5):
    try:
        # Get place details from Google Maps API
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "photo",
            "key": GOOGLE_MAPS_API_KEY,
        }
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()

        # Check for errors
        if details_response.status_code != 200 or "error_message" in details_data:
            raise HTTPException(
                status_code=details_response.status_code,
                detail=details_data.get("error_message", "Unknown error occurred."),
            )

        # Get all photo references
        photo_references = details_data.get("result", {}).get("photos", [])
        if not photo_references:
            return {"photo_urls": []}

        # Fetch multiple photo URLs up to the limit
        photo_urls = []
        for photo_ref in photo_references[:limit]:
            photo_reference = photo_ref["photo_reference"]
            photo_url = (
                f"https://maps.googleapis.com/maps/api/place/photo"
                f"?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
            )
            photo_urls.append(photo_url)

        return {"photo_urls": photo_urls}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch photos: {str(e)}",
        )

#review endpoints:
@app.post("/admin/refresh-reviews-cache")
async def refresh_reviews_cache(background_tasks: BackgroundTasks):
    async def update_reviews_cache():
        try:
            reviews_ref = db.collection("reviews").stream()
            reviews_data = {}

            for doc in reviews_ref:
                # Get the document data
                data = doc.to_dict()
                
                # Extract metadata
                metadata = data["metadata"]
                
                # Combine Google and Yelp reviews
                reviews_list = []
                
                # Add Google reviews
                google_reviews = data.get("google_reviews", [])
                reviews_list.extend(google_reviews)
                
                # Add Yelp reviews
                yelp_reviews = data.get("yelp_reviews", [])
                reviews_list.extend(yelp_reviews)
                
                # Create the structured data
                restaurant_reviews = {
                    "google_place_id": metadata.get("google_place_id"),
                    "gmaps_name": metadata.get("gmaps_name"),
                    "yelp_name": metadata.get("yelp_name"),
                    "yelp_business_id": metadata.get("yelp_business_id"),
                    "fetch_time": metadata.get("fetch_time"),
                    "reviews": reviews_list
                }
                
                # Store using google_place_id as key
                if metadata.get("google_place_id"):
                    reviews_data[metadata["google_place_id"]] = restaurant_reviews

            # Write to cache file
            async with aiofiles.open('reviews_cache.json', 'w') as f:
                await f.write(json.dumps(reviews_data))

            print("Reviews cache updated successfully.")

        except Exception as e:
            print(f"Error updating reviews cache: {str(e)}")

    # Run the update process in the background
    background_tasks.add_task(update_reviews_cache)
    return {"message": "Reviews cache refresh started"}

@app.get("/restaurants/{place_id}/reviews", response_model=RestaurantReviews)
async def get_restaurant_reviews(place_id: str):
    """
    Retrieve all reviews for a specific restaurant by its Google Place ID.
    The response includes both Google and Yelp reviews combined into a single list.
    """
    try:
        # Ensure the cache file exists
        if not os.path.exists('reviews_cache.json'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Reviews cache file not found. Please refresh the cache."
            )

        # Load the cache
        async with aiofiles.open('reviews_cache.json', 'r') as f:
            content = await f.read()
            reviews_data = json.loads(content)

        # Get reviews for the specific restaurant
        restaurant_reviews = reviews_data.get(place_id)
        
        if not restaurant_reviews:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reviews not found for restaurant with place_id {place_id}"
            )

        return restaurant_reviews

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reviews: {str(e)}"
        )
    


# Pydantic model for achievement
class Achievement(BaseModel):
    id: str
    points: int
    description: str
    repeatable: bool
    
@app.post("/achievements/add")
async def add_achievement(achievement: Achievement):
    try:
        # Extract the id and other fields from the Achievement object
        achievement_data = achievement.dict()
        doc_id = achievement_data.pop("id")  # Extract the id and remove it from the document data

        # Use doc_id as the document ID and add the rest of the data
        db.collection("achievements").document(doc_id).set(achievement_data)

        return {"message": f"Achievement '{doc_id}' added successfully."}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add achievement: {str(e)}"
        )


async def check_and_award_achievements(username: str, achievement_id: str):
    # Fetch user document
    user_ref = db.collection("users").document(username)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail=f"User {username} not found")

    user_data = user_doc.to_dict()
    current_achievements = set(user_data.get("achievements", []))

    # Fetch the achievement by id
    achievement_ref = db.collection("achievements").document(achievement_id)
    achievement_doc = achievement_ref.get()
    if not achievement_doc.exists:
        raise HTTPException(status_code=404, detail=f"Achievement '{achievement_id}' not found")

    achievement = achievement_doc.to_dict()

    # Check if the achievement can be added
    new_achievements = []
    total_points_awarded = 0

    if achievement["repeatable"] or achievement_id not in current_achievements:
        current_achievements.add(achievement_id)
        new_achievements.append(achievement_id)
        total_points_awarded += achievement["points"]

    # Update user achievements and points
    if new_achievements:
        user_ref.update({
            "achievements": list(current_achievements),
            "points.generalPoints": firestore.Increment(total_points_awarded)
        })

    return new_achievements






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)