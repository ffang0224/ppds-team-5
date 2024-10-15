# Playlists Postman Section:

PUT Endpoint:
Request: http://127.0.0.1:8000/users/bob_williams/playlists/1CIwF7zysvoCUfb8MY5k

Body: Select raw, and paste the following



    {"author": "Bob Williams",
    
    "description": "Relaxing Chinese tea house music",
    
    "name": "Chinese Tea House",
    
    "restaurants": ["/restaurants/SPICE001", "/restaurants/SPICE002"],

    "username": "bob_williams"}



POST Endpoint:
Request: http://127.0.0.1:8000/users/bob_williams/playlists

Body: Select raw and paste the following


    {"author": "Bob Williams",

    "description": "Relaxing Chinese tea house music",
    
    "name": "Chinese Tea House",
    
    "restaurants": ["/restaurants/SPICE001", "/restaurants/SPICE002"],
    
    "username": "bob_williams"}


# Restaurant Postman Section:
POST Endpoint:
Request: http://127.0.0.1:8000/restaurants

Body: Select raw, JSON format and paste the following

{
  "restaurantId": "testing",
  "name": "The Big Apple Diner",
  "location": {
    "address": "123 Broadway",
    "city": "New York",
    "country": "USA",
    "postalCode": "10007",
    "state": "NY",
    "coordinates": {
      "latitude": 40.7128,
      "longitude": -74.0060
    }
  },
  "contact": {
    "email": "info@bigapplediner.com",
    "phone": "+12125551234",
    "website": "https://www.bigapplediner.com"
  },
  "cuisines": "American",
  "dietaryOptions": {
    "glutenFree": true,
    "halal": false,
    "kosher": false,
    "vegan": false,
    "vegetarian": true
  },
  "features": {
    "delivery": true,
    "dineIn": true,
    "outdoorSeating": false,
    "parking": true,
    "takeout": true,
    "wifi": true
  },
  "hours": {
    "monday": {"open": "00:00", "close": "23:59"},
    "tuesday": {"open": "00:00", "close": "23:59"},
    "wednesday": {"open": "00:00", "close": "23:59"},
    "thursday": {"open": "00:00", "close": "23:59"},
    "friday": {"open": "00:00", "close": "23:59"},
    "saturday": {"open": "00:00", "close": "23:59"},
    "sunday": {"open": "00:00", "close": "23:59"}
  },
  "images": [
    "https://example.com/bigapplediner1.jpg",
    "https://example.com/bigapplediner2.jpg"
  ],
  "popularDishes": ["Pancakes", "Cheeseburger", "Apple Pie"],
  "priceRange": "$$",
  "reservationLink": "https://reservations.bigapplediner.com",
  "specialties": ["All-Day Breakfast", "Mile-High Sandwiches"],
  "tags": ["24/7", "classic", "family-friendly"]
}

PUT Endpoint:
Request: http://127.0.0.1:8000/restaurants/TestRestaurant

Body: Select raw, JSON format and paste the following

{
  "restaurantId": "TestRestaurant",
  "name": "Dolar Shop",
  "location": {
    "address": "Test PUT",
    "city": "New York",
    "country": "USA",
    "postalCode": "10003",
    "state": "NY",
    "coordinates": {
      "latitude": -40.7128,
      "longitude": 54.0060
    }
  },
  "contact": {
    "email": "info@dolarshop.com",
    "phone": "Test PUT",
    "website": "https://www.dolarshop.com"
  },
  "cuisines": "Asian",
  "dietaryOptions": {
    "glutenFree": true,
    "halal": false,
    "kosher": false,
    "vegan": true,
    "vegetarian": true
  },
  "features": {
    "delivery": true,
    "dineIn": true,
    "outdoorSeating": false,
    "parking": true,
    "takeout": true,
    "wifi": true
  },
  "hours": {
    "monday": {"open": "13:00", "close": "20:00"},
    "tuesday": {"open": "10:00", "close": "23:59"},
    "wednesday": {"open": "10:00", "close": "23:59"},
    "thursday": {"open": "10:00", "close": "23:59"},
    "friday": {"open": "10:00", "close": "23:59"},
    "saturday": {"open": "10:00", "close": "23:59"},
    "sunday": {"open": "10:00", "close": "23:59"}
  },
  "images": [],
  "popularDishes": ["Pancakes", "Cheeseburger", "Apple Pie"],
  "priceRange": "$$$",
  "reservationLink": "https://reservations.dolarshop.com",
  "specialties": ["All-Day Breakfast", "Mile-High Sandwiches"],
  "tags": ["classic", "family-friendly","kids playground"]
}