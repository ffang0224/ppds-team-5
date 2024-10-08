# Python Database Manager

## Features

- Manage "Users", "Restaurants", and "Playlists" collections (modifiable) on a Google Firebase Firestore NoSQL database.
- Add new users, restaurants or restaurant playlists.
- View all existing data in the collections.
- Update current information on the database.
- User input for manual insertion of data.
- Batch addition of data with CSV file.

## Description of Our Data Model:
Our data model will be designed with a NoSQL type database. Our Foodify program will revolve around three main entities, users, restaurants, and playlists, with the username attribute being the primary key for all of our entities. The first entity is the Users entity and it includes the following attributes: username (type: string), email (type: string), firstName (type: string), and lastName (type: string), playlists which is an array of references to playlist objects where each playlist is referenced by a unique identifier, and lastly the points map, which is broken down into generalPoints (type: int), postPoints (type: int), and reviewPoints (type: int).
Next, we have the Restaurants entity which includes the cuisines attribute (type: string) which indicates the types of food offered. Next the Restaurants entity includes three separate arrays for reviews: instagramReviews, mapsReviews, and redditReviews. For instagramReviews, and redditReviews every review array has a series of maps, and each one of those maps have details such as the commentAuthor (type: string), review (type: string). Moving to mapsReviews, it has the same attributes as instagramReviews and redditReviews with the additional attribute stars (number), which is a rating score for the restaurant,and also the location attribute stored as a geopoint that has the restaurant’s latitude and longitude. RestaurantImage attribute stores a URL to an image of the restaurant. Finally, the summary attribute provides a brief overview of the restaurant. 
Lasly, our last entity which is the playlists entity, which is designed to organize restaurant collections, similar to music playlists in a way. This entity has attributes like author  (type: string), which gives us the user who created the playlist, description  (type: string) that gives a brief overview of the playlist, and name  (type: string), which specifies the title of the playlist. The restaurants attribute is an array of references, with each element pointing to a specific restaurant entity from our restaurant entity. 

## Why we chose a NoSQL type database over SQL

Firstly, our entities and their attributes include a lot of referencing to other entities. Moreover, a NoSQL type database stores data in collections of documents rather than storing data in tables with rows and columns like SQL. That being said, it makes it easier to nest these entities and access their attributes. 
Also, considering that we have certain attributes that may not necessarily fit neatly into a a fixed schema or table, thus we are working with unstructured data. For instance, when it comes to the reviews that the users will write, one user may include more details, such as a comment, stars, and a rating, while others may keep it more brief with just a rating. For this reason we choose a NoSQL type database, as it can handle data that may have varying attributes without having to define a structured/fixed schema.

## Prerequisites

- Python 3.13.0 or higher.
- pip (Python package manager)
- Google Firebase account

## Setup

1. Clone this repository: \
`git clone https://github.com/ffang0224/ppds-team-5.git`

2. Navigate to the project directory:

```bash
cd path/to/ppds-team-5
```

3. Create a virtual environment (optional):

```python

python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS and Linux:
source .venv/bin/activate

```

4. Install dependencies: \
`pip install -r requirements.txt`

5. Initialize a Firebase Firestore Instance and download credentials. \
Add credentials to the root folder with the name *"firebase_credentials.json"*. Credentials can be found under **Project Settings -> Service Accounts**

## Usage

To run the script:
`python3 script.py`

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

## Contributing

Contributions to improve the application are welcome. Please feel free to submit a Pull Request.

## Licensing

Available under the [MIT License](https://opensource.org/license/mit).