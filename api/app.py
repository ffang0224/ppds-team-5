from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase app
cred = credentials.Certificate('../python_script/firebase_credentials.json')  # Adjust this path if necessary
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

app = FastAPI()

# Helper function to convert Firestore-specific types to JSON-serializable types
def convert_to_json_serializable(obj):
    """
    Convert Firestore-specific types to JSON-serializable types.
    """
    if isinstance(obj, firestore.DocumentReference):
        return obj.path  # Convert Firestore reference to string (returns the reference path)
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}  # Recursively handle nested dictionaries
    elif isinstance(obj, list):
        return [convert_to_json_serializable(i) for i in obj]  # Recursively handle lists
    else:
        return obj  # Return the object as-is if it doesn't need special conversion

# Root endpoint for testing if FastAPI is running
@app.get("/")
async def root():
    return {"message": "FastAPI is running"}

# Endpoint to fetch all users from Firestore
@app.get("/users")
async def get_users():
    print("Fetching users from Firestore...")  # Debug message
    try:
        docs = db.collection("users").stream()
        print("Users collection retrieved from Firestore")  # Debug message
        users = []
        for doc in docs:
            print(f"Processing user: {doc.id}")  # Debug message
            user_data = doc.to_dict()
            json_friendly_data = {k: convert_to_json_serializable(v) for k, v in user_data.items()}
            users.append(json_friendly_data)
        print(f"Users found: {users}")  # Final debug message
        return users
    except Exception as e:
        print(f"Error fetching users: {e}")  # Print the error
        return {"error": str(e)}
