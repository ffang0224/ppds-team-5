import praw
import csv
import os

# Manually load environment variables from .env file
def load_env_variables(file_path="../.env"):
    """Load environment variables from a .env file."""
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Load environment variables
load_env_variables()

# Retrieve Reddit credentials from environment variables
client_id = os.getenv('REDDIT_CLIENT_ID')
client_secret = os.getenv('REDDIT_CLIENT_SECRET')
user_agent = os.getenv('REDDIT_USER_AGENT')

# Set the number of posts and the subreddit to search
NUMBER_OF_POSTS = 500
SUBREDDIT_NAME = 'FoodNYC'

# Initialize Reddit instance with credentials
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)

# Define the subreddit for searching
subreddit = reddit.subreddit(SUBREDDIT_NAME)

# Open a CSV file to write the results
with open('reddit_posts_with_comments.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Title', 'Text', 'Comments'])

    # Search the subreddit for posts
    for submission in subreddit.new(limit=NUMBER_OF_POSTS):  # Fetches latest posts
        # Fetch top-level comments for the post
        submission.comments.replace_more(limit=0)  # Ensure no "load more comments" placeholder
        comments = [comment.body for comment in submission.comments.list()]
        
        # Write to CSV
        writer.writerow([submission.title, submission.selftext, " | ".join(comments)])

print("Data saved to r_FoodNYC_posts_with_comments.csv")
