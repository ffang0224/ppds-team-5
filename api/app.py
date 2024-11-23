from fastapi import FastAPI, HTTPException, status, BackgroundTasks
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

# Initialize Firebase app
cred = credentials.Certificate('../python_script/firebase_credentials.json')
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


# Original Models
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

# Create a Pydantic model for the User update request
class UserUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    createdAt: str

class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = ""
    restaurants: List[str] = Field(default_factory=list)
    color: str = "#f97316"
    author: str
    username: str

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistRead(PlaylistBase):
    id: str
    createdAt: str

# Updated Restaurant Models
class Location(BaseModel):
    lat: float
    lng: float

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

class RestaurantListBase(BaseModel):
    name: str
    description: Optional[str] = ""
    restaurants: List[str] = Field(default_factory=list)  # List of place_ids
    color: str = "#f97316"
    author: str
    username: str

class RestaurantListCreate(RestaurantListBase):
    pass

class RestaurantListRead(RestaurantListBase):
    id: str
    createdAt: str

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
            "lists": []  # Added for restaurant lists
        }

        db.collection("users").document(user.username).set(user_data)
        
        return {
            "message": "User created successfully",
            "username": user.username
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
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
    
# --- Original Playlist Endpoints ---
@app.post("/users/{username}/playlists", status_code=status.HTTP_201_CREATED)
async def create_playlist(username: str, playlist: PlaylistCreate):
    try:
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        if playlist.username != username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create playlist for another user"
            )

        playlist_ref = db.collection("users").document(username).collection("playlists").document()
        
        playlist_data = {
            **playlist.dict(),
            "id": playlist_ref.id,
            "createdAt": datetime.utcnow().isoformat()
        }

        playlist_ref.set(playlist_data)

        db.collection("users").document(username).update({
            "playlists": firestore.ArrayUnion([playlist_ref.id])
        })

        return {
            "message": "Playlist created successfully",
            "id": playlist_ref.id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/playlists", response_model=List[PlaylistRead])
async def get_user_playlists(username: str):
    try:
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        playlists = db.collection("users").document(username).collection("playlists").get()
        return [validate_and_serialize(doc.to_dict()) for doc in playlists]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/playlists/{playlist_id}", response_model=PlaylistRead)
async def get_playlist(username: str, playlist_id: str):
    try:
        doc = db.collection("users").document(username).collection("playlists").document(playlist_id).get()
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

@app.put("/users/{username}/playlists/{playlist_id}")
async def update_playlist(username: str, playlist_id: str, playlist: PlaylistCreate):
    try:
        playlist_ref = db.collection("users").document(username).collection("playlists").document(playlist_id)
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

@app.delete("/users/{username}/playlists/{playlist_id}")
async def delete_playlist(username: str, playlist_id: str):
    try:
        user_ref = db.collection("users").document(username)
        playlist_ref = user_ref.collection("playlists").document(playlist_id)

        if not playlist_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        playlist_ref.delete()

        user_ref.update({
            "playlists": firestore.ArrayRemove([playlist_id])
        })

        return {"message": "Playlist deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/lists", response_model=List[PlaylistRead])
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

@app.get("/users/{username}/lists/{list_id}", response_model=PlaylistRead)
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
async def update_playlist(username: str, list_id: str, playlist: PlaylistCreate):
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

@app.delete("/users/{username}/lists/{list_id}")
async def delete_playlist(username: str, list_id: str):
    try:
        user_ref = db.collection("users").document(username)
        playlist_ref = user_ref.collection("lists").document(list_id)

        if not playlist_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        playlist_ref.delete()

        user_ref.update({
            "lists": firestore.ArrayRemove([list_id])
        })

        return {"message": "Playlist deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
@app.post("/admin/refresh-restaurant-cache")
async def refresh_restaurant_cache(background_tasks: BackgroundTasks):
    async def update_cache():
        try:
            restaurants = db.collection("restaurants").get()
            restaurant_list = []
            
            for doc in restaurants:
                data = doc.to_dict()
                if 'location' in data and isinstance(data['location'], GeoPoint):
                    data['location'] = convert_geopoint(data['location'])
                
                restaurant_data = {
                    'place_id': data.get('place_id', ''),
                    'name': data.get('name', ''),
                    'rating': float(data.get('rating', 0.0)),
                    'user_ratings_total': int(data.get('user_ratings_total', 0)),
                    'address': data.get('address', ''),
                    'location': data['location'],
                    'price_level': data.get('price_level'),
                    'types': data.get('types', []),
                    'created_at': convert_datetime(data.get('created_at')),
                    'updated_at': convert_datetime(data.get('updated_at'))
                }
                restaurant_list.append(restaurant_data)
            
            async with aiofiles.open('restaurant_cache.json', 'w') as f:
                await f.write(json.dumps(restaurant_list))
                
        except Exception as e:
            print(f"Error updating cache: {str(e)}")

    background_tasks.add_task(update_cache)
    return {"message": "Cache refresh started"}

# Replace your existing get_restaurants endpoint
@app.get("/restaurants", response_model=List[Restaurant])
async def get_restaurants(
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    price_level: Optional[int] = None
):
    try:
        if not os.path.exists('restaurant_cache.json'):
            return await get_restaurants_from_firestore()
            
        async with aiofiles.open('restaurant_cache.json', 'r') as f:
            content = await f.read()
            restaurants = json.loads(content)
            
        filtered_restaurants = restaurants
        
        if search:
            search_lower = search.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if search_lower in r['name'].lower() or
                any(search_lower in t.lower() for t in r['types'])
            ]
            
        if cuisine:
            cuisine_lower = cuisine.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if cuisine_lower in [t.lower() for t in r['types']]
            ]
            
        if price_level is not None:
            filtered_restaurants = [
                r for r in filtered_restaurants
                if r['price_level'] == price_level
            ]
            
        return filtered_restaurants
        
    except Exception as e:
        return await get_restaurants_from_firestore()
    
# Fallback function for when cache fails
async def get_restaurants_from_firestore():
    restaurants = db.collection("restaurants").get()
    return [validate_and_serialize(doc.to_dict()) for doc in restaurants]

# @app.get("/restaurants/{restaurant_id}", response_model=Restaurant)
# async def get_restaurant(restaurant_id: str):
#     try:
#         # Get restaurant document asynchronously
#         doc_ref = db.collection("restaurants").document(restaurant_id)
#         doc = await doc_ref.get()
        
#         if not doc.exists:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Restaurant with id {restaurant_id} not found"
#             )
        
#         # Convert Firestore document to dict and add id
#         restaurant_data = doc.to_dict()
#         restaurant_data["id"] = doc.id
        
#         # Validate and return using Pydantic model
#         return Restaurant(**restaurant_data)
        
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve restaurant: {str(e)}"
#         )

@app.get("/restaurants/{place_id}", response_model=Restaurant)
async def get_restaurant(place_id: str):
    try:
        # Query restaurant collection by place_id
        restaurants_ref = db.collection("restaurants")
        query = restaurants_ref.where("place_id", "==", place_id).limit(1)
        docs = query.stream()
        
        restaurant_doc = next(docs, None)
        
        if not restaurant_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant with place_id {place_id} not found"
            )
        
        # Convert Firestore document to dict and add id
        restaurant_data = restaurant_doc.to_dict()
        restaurant_data["id"] = restaurant_doc.id
        
        # Validate and format the data
        formatted_data = validate_and_serialize(restaurant_data)
        
        # Validate and return using Pydantic model
        return Restaurant(**formatted_data)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve restaurant: {str(e)}"
        )

# --- New Restaurant List Endpoints ---
@app.post("/users/{username}/lists", status_code=status.HTTP_201_CREATED)
async def create_restaurant_list(username: str, restaurant_list: RestaurantListCreate):
    try:
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        if restaurant_list.username != username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create list for another user"
            )

        list_ref = db.collection("users").document(username).collection("lists").document()
        
        list_data = {
            **restaurant_list.dict(),
            "id": list_ref.id,
            "createdAt": datetime.utcnow().isoformat()
        }

        list_ref.set(list_data)

        db.collection("users").document(username).update({
            "lists": firestore.ArrayUnion([list_ref.id])
        })

        return {
            "message": "Restaurant list created successfully",
            "id": list_ref.id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/lists", response_model=List[RestaurantListRead])
async def get_user_restaurant_lists(username: str):
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
@app.put("/users/{username}/lists/{list_id}")
async def update_restaurant_list(username: str, list_id: str, restaurant_list: RestaurantListCreate):
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

        # Verify list exists
        if not list_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant list not found"
            )

        # Delete list
        list_ref.delete()

        # Update user's lists array
        user_ref.update({
            "lists": firestore.ArrayRemove([list_id])
        })

        return {"message": "Restaurant list deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Added some utility endpoints for restaurants
@app.get("/restaurants/search")
async def search_restaurants(query: str, cuisine: Optional[str] = None, price_level: Optional[int] = None):
    try:
        restaurants_ref = db.collection("restaurants")
        
        # Start with base query
        query_ref = restaurants_ref

        # Apply filters if provided
        if cuisine:
            query_ref = query_ref.where("types", "array_contains", cuisine.lower())
        
        if price_level is not None:
            query_ref = query_ref.where("price_level", "==", price_level)

        # Get all matching documents
        restaurants = query_ref.get()
        
        # Filter by name search (done in memory since Firestore doesn't support case-insensitive search)
        results = []
        query_lower = query.lower()
        for doc in restaurants:
            restaurant = doc.to_dict()
            if (query_lower in restaurant['name'].lower() or
                any(query_lower in type_.lower() for type_ in restaurant['types'])):
                results.append(validate_and_serialize(restaurant))

        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/restaurants/popular")
async def get_popular_restaurants(limit: int = 10):
    try:
        restaurants = (db.collection("restaurants")
                      .order_by("rating", direction=firestore.Query.DESCENDING)
                      .order_by("user_ratings_total", direction=firestore.Query.DESCENDING)
                      .limit(limit)
                      .get())
        
        return [validate_and_serialize(doc.to_dict()) for doc in restaurants]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/restaurants/nearby")
async def get_nearby_restaurants(lat: float, lng: float, radius_km: float = 2.0):
    try:
        # Note: This is a simple implementation. For production, you'd want to use
        # geohashing or a proper geo-querying solution
        
        # Convert km to lat/lng degrees (approximate)
        lat_degree = radius_km / 111.0  # 111km per degree of latitude
        lng_degree = radius_km / (111.0 * cos(radians(lat)))  # Adjust for longitude

        restaurants = db.collection("restaurants").get()
        
        nearby = []
        for doc in restaurants:
            restaurant = doc.to_dict()
            r_lat = restaurant['location']['lat']
            r_lng = restaurant['location']['lng']
            
            # Simple distance check
            if (abs(r_lat - lat) <= lat_degree and 
                abs(r_lng - lng) <= lng_degree):
                nearby.append(validate_and_serialize(restaurant))

        return nearby
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# @app.get("/users/{username}/lists/{list_id}/restaurants", response_model=List[Restaurant])
# async def get_restaurants_in_list(username: str, list_id: str):
#     try:
#         # Get the list
#         list_doc = db.collection("users").document(username).collection("lists").document(list_id).get()
        
#         if not list_doc.exists:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Restaurant list not found"
#             )

#         list_data = list_doc.to_dict()
#         restaurant_ids = list_data.get('restaurants', [])

#         # Get all restaurants in the list
#         restaurants = []
#         for place_id in restaurant_ids:
#             restaurant_doc = db.collection("restaurants").document(place_id).get()
#             if restaurant_doc.exists:
#                 restaurants.append(validate_and_serialize(restaurant_doc.to_dict()))

#         return restaurants
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)