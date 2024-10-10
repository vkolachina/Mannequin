import os
import sys
import requests
import logging
import time
import csv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_API_URL = "https://api.github.com"
TOKEN = os.getenv('PERSONAL_ACCESS_TOKEN')
CSV_FILE = os.getenv('CSV_FILE')
GITHUB_REPO = os.getenv('GITHUB_REPO')

if not TOKEN:
    logging.error("PERSONAL_ACCESS_TOKEN not found. Please set the PERSONAL_ACCESS_TOKEN environment variable.")
    sys.exit(1)

if not CSV_FILE:
    logging.error("CSV_FILE not found. Please set the CSV_FILE environment variable.")
    sys.exit(1)

if not GITHUB_REPO:
    logging.error("GITHUB_REPO not found. Please set the GITHUB_REPO environment variable.")
    sys.exit(1)

logging.info(f"CSV file path: {CSV_FILE}")

def validate_input(username, repo, permission):
    valid_permissions = ['pull', 'push', 'admin', 'contributor']
    if not username or not repo or not permission:
        raise ValueError("Username, repository, and permission must be provided")
    if permission.lower() not in valid_permissions:
        raise ValueError(f"Invalid permission. Must be one of {valid_permissions}")

def make_request(url, method='get', data=None, max_retries=3):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    for attempt in range(max_retries):
        try:
            if method == 'get':
                response = requests.get(url, headers=headers)
            elif method == 'put':
                response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                sleep_time = max(reset_time - time.time(), 0) + 1
                logging.warning(f"Rate limit hit. Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)
                continue
            
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            logging.warning(f"Request failed. Retrying... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)  # Exponential backoff

def add_user_to_repo(username, repo, permission):
    url = f"{GITHUB_API_URL}/repos/{repo}/collaborators/{username}"
    
    # Map 'contributor' to 'push' permission
    if permission.lower() == 'contributor':
        permission = 'push'
    
    data = {"permission": permission.lower()}
    try:
        response = make_request(url, method='put', data=data)
        logging.info(f"Successfully added {username} to {repo} with {permission} permission")
    except requests.RequestException as e:
        logging.error(f"Failed to add {username} to {repo}. Error: {str(e)}")

def main():
    try:
        with open(CSV_FILE, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header row
            for row in csv_reader:
                if len(row) == 4:
                    mannequin_user, mannequin_id, target_user, role = row
                    try:
                        validate_input(target_user, GITHUB_REPO, role)
                        add_user_to_repo(target_user, GITHUB_REPO, role)
                    except ValueError as e:
                        logging.error(f"Invalid input: {row}. Error: {str(e)}")
                    except Exception as e:
                        logging.error(f"Unexpected error processing: {row}. Error: {str(e)}")
    except FileNotFoundError:
        logging.error(f"CSV file not found: {CSV_FILE}")
        sys.exit(1)

if __name__ == "__main__":
    main()