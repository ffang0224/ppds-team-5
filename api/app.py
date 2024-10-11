from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore
from pydantic import BaseModel
from typing import List, Dict

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
async def get_user(collectionName:str, id: str):
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
async def get_users(collectionName: str):
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
    
    
# ref = db.collection("users").document(user_id)
# ref.update(newdata.dict())


# DELETE
# ref = db.collection("users").document(user_id).delete()