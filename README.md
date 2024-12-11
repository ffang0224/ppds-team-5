# Python Database Manager

## Features

- Manage "Users," "Restaurants," "AllLists," and "Reviews" collections on a Google Firebase Firestore NoSQL database.
- Add new users, restaurants, or restaurant lists.
- View all existing data in the collections.
- Update existing information in the database.
- Provide user input for manual data insertion.
- Perform batch data additions using CSV files.

## Description of Our Data Model

Our data model is designed using a NoSQL database structure. The Foodify program revolves around four main entities: Users, Restaurants, Reviews, and allLists. The primary key for the Users, Restaurants, and allLists entities is the username attribute.

The Users entity includes the following attributes:

username, email, firstName, and lastName (all of type string).
playlists: an array of references to Playlist objects, where each playlist is identified by a unique ID.
points: a map broken down into generalPoints, postPoints, and reviewPoints (all of type int).
The Restaurants entity includes several attributes, many of which are maps:

- Contact: Stores a collection of the restaurant’s email, phone, and website (all of type string).
- Dietary Options: Contains five boolean attributes indicating if the restaurant caters to Kosher, Halal, Gluten-Free, Vegan, or Vegetarian preferences.
- Features: Includes six boolean attributes for additional services: delivery, dineIn, outdoorSeating, parking, takeout, and wifi.
- Hours: Stores the open and close times for each day of the week (type string).
- Location: A map containing the address details, including address, city, state, country, postalCode (all of type string), and geographical coordinates (latitude and longitude of type GeoPoint).

The Reviews entity includes the following attributes:

- commentAuthor (type string): The author of the comment.
- restaurantId (type string): A reference to the restaurant being reviewed.
- review (type string): The content of the review.
- source (type string): Indicates where the review originates, such as Google Maps, Reddit, or Instagram.
- stars (type number): A rating out of 5.

The allLists entity organizes collections of restaurants in a way similar to music playlists. It includes the following attributes:

- author (type string): Identifies the user who created the playlist.
- description (type string): Provides a brief overview of the playlist.
- name (type string): Specifies the title of the playlist.
- restaurants: An array of references, where each element points to a specific restaurant entity in the Restaurants collection.

## Why we chose a NoSQL type database over SQL

Our entities contain numerous references to other entities, and a NoSQL database stores data as documents rather than in tables, making it easier to nest and access attributes. Since some attributes don't fit neatly into a fixed schema, we're working with unstructured data. For example, user reviews may vary in detail—some may include comments and ratings, while others may only have a rating. A NoSQL database is ideal for handling such variable data without needing a rigid schema.

## Prerequisites

- Python 3.13.0 or higher.
- pip (Python package manager)
- Google Firebase account
- Google Cloud API Key

## Setup

1. **Clone this repository**:  
   `git clone https://github.com/ffang0224/ppds-team-5.git`

2. **Navigate to the project directory**:  
   `cd path/to/ppds-team-5`

3. **Create a virtual environment (optional)**:

   - On Windows:  
     `python -m venv .venv`  
     `.venv\Scripts\activate`
   - On macOS and Linux:  
     `python -m venv .venv`  
     `source .venv/bin/activate`

4. **Install dependencies**:  
   `pip install -r requirements.txt`

5. **Set up Firebase Firestore**:

   - Initialize a Firebase Firestore instance.
   - Download the Firebase Admin credentials from **Project Settings -> Service Accounts**.
   - Save the credentials JSON file in the root folder with the name `firebase_credentials.json`.

6. **Create a `.env` file** in the "api" directory:

   - Add the Google Maps API key in the following format:
     ```
     GOOGLE_MAPS_API_KEY=YOUR_API_KEY_HERE
     ```

## Script Usage

To run the script:
`python3 python_script/script.py`

Follow the prompts on screen to interact with the database:

```none
--- Restaurant, Playlist, and User Manager ---
1. Add a new restaurant manually
2. Add restaurants from CSV
3. Update a restaurant
4. Delete a restaurant
5. Read a restaurant
6. List all restaurants

7. Add a new playlist manually
8. Add playlists from CSV
9. Update a playlist
10. Delete a playlist
11. Read a playlist
12. List all playlists

13. Add a new user manually
14. Add users from CSV
15. Update a user
16. Delete a user
17. Read a user
18. List all users

19. Exit
Enter your choice (1-19):
```

## API

Our application provides API endpoints to manage users, reviews, playlists, restaurants, and achievements in the database. These endpoints allow adding new entries, updating existing ones, deleting entries, and retrieving information for all entities. Below are the key actions supported for each entity:

- **GET**: Retrieves an entry or lists all entries in the specified collection.

- **POST**: Adds a new entry to the database.

- **PUT**: Updates an existing entry in the database.

- **DELETE**: Deletes an entry from the database.

These actions allow full management of the entities within the database, providing flexibility in how users interact with and modify data.

To try it out, use the following command after installing `requirements.txt`:

```none
cd api
uvicorn app:app
```

After this, go to <http://127.0.0.1:8000/docs> to explore all the endpoints.

<br>
<br>

Sample data for Postman is included in the API folder. Import the JSON as raw text (just copy and paste into the field) on Postman and run the server to try the API endpoints.

![alt text](image.png)
![alt text](image-1.png)

## Contributing

Contributions to improve the application are welcome. Please feel free to submit a Pull Request.

## Licensing

Available under the [MIT License](https://opensource.org/license/mit).
