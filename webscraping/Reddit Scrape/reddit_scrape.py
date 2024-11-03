import praw
import csv
import os

# Manually load environment variables from .env file
def load_env_variables(file_path="../.env"):
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

NUMBER_OF_POSTS = 200
KEYWORD = 'NYC restaurants'

# Initialize Reddit instance with your credentials
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)

# Define the subreddit and keyword you're interested in
subreddit = reddit.subreddit('all')  # 'all' searches across all subreddits
keyword = KEYWORD

# Open a CSV file to write the results
with open('reddit_posts.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Title', 'Text', 'Score', 'URL'])

    # Search Reddit for the keyword
    for submission in subreddit.search(keyword, limit=NUMBER_OF_POSTS):
        writer.writerow([submission.title, submission.selftext, submission.score, submission.url])

print("Data saved to reddit_posts.csv")
