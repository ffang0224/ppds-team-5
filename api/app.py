import firebase_admin
from fastapi import FastAPI, HTTPException
from firebase_admin import credentials, firestore
from pydantic import BaseModel
from typing import List, Dict
from google.cloud import firestore as gc_firestore
from google.cloud.firestore import GeoPoint

# Initialize Firebase app
cred = credentials.Certificate('../python_script/firebase_credentials.json')  # Adjust this path if necessary
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

app = FastAPI()

# Pydantic model to validate incoming user data
class User(BaseModel):
    email: str
    firstName: str
    lastName: str
    username: str
    points: Dict[str, int]  # e.g., {"generalPoints": 100, "postPoints": 50, "reviewPoints": 30}
    playlists: List[str]  # list of playlist IDs

# Helper function to convert Firestore-specific types to JSON-serializable types
def convert_to_json_serializable(obj):
    if isinstance(obj, firestore.DocumentReference):
        return obj.path  # Convert Firestore reference to string
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}  # Recursively handle nested dictionaries
    elif isinstance(obj, list):
        return [convert_to_json_serializable(i) for i in obj]  # Recursively handle lists
    return obj  # Return the object as-is if it doesn't need special conversion

# Function to add user to Firestore
def add_user_to_firestore(user_data, user_collection_name, playlist_collection_name):
    user_data.playlists = [db.collection(playlist_collection_name).document(playlist_id) for playlist_id in user_data.playlists]
    doc_ref = db.collection(user_collection_name).document(user_data.username)
    doc_ref.set(user_data)
    print(f"User added to collection {user_collection_name} with username: {user_data.username}")

# Root endpoint for testing if FastAPI is running
@app.get("/")
async def root():
    return {"message": "FastAPI is running"}


# Fetch a single user by their username (entity_id)
@app.get("/{collectionName}/{id}")
async def get_item(collectionName:str, id: str):
    try:
        # Retrieve the user document by username
        user_doc = db.collection(collectionName).document(id).get()
        
        # Check if the document exists
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail=f"User with username '{id}' not found")
        
        # Convert Firestore document to dictionary
        user_data = user_doc.to_dict()
        json_friendly_data = {k: convert_to_json_serializable(v) for k, v in user_data.items()}
        
        return json_friendly_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user: {e}")


# Fetch all users from Firestore
@app.get("/{collectionName}")
async def get_items(collectionName: str):
    try:
        docs = db.collection(collectionName).stream()
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            json_friendly_data = {k: convert_to_json_serializable(v) for k, v in user_data.items()}
            users.append(json_friendly_data)
        if len(users) == 0:
            raise HTTPException(status_code=404, detail=f"Collection with name '{collectionName}' not found.")
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {e}")
    
@app.post("/users")
async def create_user(user: User):
    try:
        user_dict = user.dict()
        db.collection("users").add(user.dict(), user_dict["username"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")

#Elyazia's Part lines 99-  136  
class Playlist(BaseModel): 
    author: str
    description: str
    name: str
    restaurants: List[str]
    username: str

@app.post("/users/{username}/playlists")
async def add_playlist(username: str, playlist: Playlist):
    try:
        user_ref = db.collection("users").document(username)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail=f"User with username '{username}' does not exist")
        playlist_data = playlist.dict()  
        user_ref.collection("playlists").add(playlist_data)
        return {"message": "Playlist added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding playlist: {e}")    

@app.put("/users/{username}/playlists/{playlist_id}")
async def update_playlist(username: str, playlist_id: str, playlist: Playlist):
    try:
        user_ref = db.collection("users").document(username)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail=f"User with username '{username}' does not exist")

        playlist_ref = user_ref.collection("playlists").document(playlist_id)
        playlist_doc = playlist_ref.get()
        if not playlist_doc.exists:
            raise HTTPException(status_code=404, detail=f"Playlist with ID '{playlist_id}' does not exist")
        playlist_data = playlist.dict()
        playlist_ref.update(playlist_data)
        return {"message": "Playlist updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating playlist: {e}")


# Minseok's Part lines 137 - 177
# Review
class Review(BaseModel):
    commentAuthor: str
    restaurantId: str
    review: str
    source: str = None
    stars: int

# Creating a new review
@app.post("/reviews")
async def add_review(review: Review):
    try:
        review_data = review.dict()
        # Add the review to Firestore
        review_ref = db.collection("reviews").add(review_data)
        return {"message": "Review added successfully", "review_id": review_ref[1].id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding review: {e}")


# Update a review
@app.put("/reviews/{review_id}")
async def update_review(review_id: str, review: Review):
    try:
        # Get the reference to the review document
        review_ref = db.collection("reviews").document(review_id)
        review_doc = review_ref.get()

        # Check if the review exists
        if not review_doc.exists:
            raise HTTPException(status_code=404, detail=f"Review with ID '{review_id}' not found")

        # Update the review in Firestore
        review_data = review.dict()
        review_ref.update(review_data)
        
        return {"message": "Review updated successfully", "review_id": review_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating review: {e}")
    


# Aru's Part: Restaurants     
class Location(BaseModel):
    address: str
    city: str
    country: str
    postalCode: str
    state: str
    coordinates: dict

    def to_geopoint(self):
        return GeoPoint(latitude=self.coordinates["latitude"], longitude=self.coordinates["longitude"])

class Restaurant(BaseModel):
    restaurantId: str
    name: str
    location: Location
    contact: Dict[str, str]
    cuisines: str
    dietaryOptions: Dict[str, bool]
    features: Dict[str, bool]
    hours: Dict[str, Dict[str, str]]
    images: List[str]
    popularDishes: List[str]
    priceRange: str
    reservationLink: str
    specialties: List[str]
    tags: List[str]

# Creating a new restaurant
@app.post("/restaurants")
async def add_restaurant(restaurant: Restaurant):
    try:
        restaurant_data = restaurant.dict()

        # Convert coordinates to GeoPoint
        geopoint = restaurant.location.to_geopoint()
        restaurant_data["location"]["coordinates"] = geopoint
        # Add the restaurant to Firestore
        restaurant_ref = db.collection("restaurants").add(restaurant_data, restaurant_data["restaurantId"])
        return {"message": "restaurant added successfully", "restaurant_id": restaurant_ref[1].id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding restaurant: {e}")

# Update a restaurant  
@app.put("/restaurants/{restaurantId}")
async def update_restaurant(restaurantId: str, restaurant: Restaurant):
    try:
        # Convert the Pydantic model to a dictionary
        restaurant_data = restaurant.dict()

        # Convert coordinates to GeoPoint
        geopoint = restaurant.location.to_geopoint()
        restaurant_data["location"]["coordinates"] = geopoint

        # Get the reference to the restaurant document
        restaurant_ref = db.collection("restaurants").document(restaurantId)
        restaurant_snapshot = restaurant_ref.get()

        # Check if the restaurant exists
        if not restaurant_snapshot.exists:
            return {"error": "Restaurant with this ID does not exist"}

        # Update the restaurant data in Firestore
        restaurant_ref.update(restaurant_data)

        return {"message": "Restaurant updated successfully", "restaurant_id": restaurantId}
    except Exception as e:
        return {"error": str(e)}


# ref = db.collection("users").document(user_id)
# ref.update(newdata.dict())


# DELETE
# ref = db.collection("users").document(user_id).delete()

@app.delete("/{collectionId}/{itemID}")
async def delete_item(collectionId: str, itemID: str):
    try:
        # Get the reference to the document
        doc_ref = db.collection(collectionId).document(itemID)
        doc = doc_ref.get()

        # Check if the document exists
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Document with ID '{itemID}' not found in collection '{collectionId}'")

        # Delete the document
        doc_ref.delete()
        return {"message": f"Document with ID '{itemID}' deleted successfully from collection '{collectionId}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {e}")



