import os
import sys
import requests
import logging
import time
import csv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_API_URL = "https://api.github.com"
TOKEN = os.getenv('GITHUB_TOKEN')
CSV_FILE = os.getenv('CSV_FILE')

if not TOKEN:
    logging.error("GITHUB_TOKEN not found. Please set the GITHUB_TOKEN environment variable.")
    sys.exit(1)

if not CSV_FILE:
    logging.error("CSV_FILE not found. Please set the CSV_FILE environment variable.")
    sys.exit(1)

def validate_input(username, org, role):
    valid_roles = ['admin', 'member', 'owner']
    if not username or not org or not role:
        raise ValueError("Username, organization, and role must be provided")
    if role.lower() not in valid_roles:
        raise ValueError(f"Invalid role. Must be one of {valid_roles}")

def make_request(url, method='get', data=None, max_retries=3):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    for attempt in range(max_retries):
        try:
            if method == 'get':
                response = requests.get(url, headers=headers)
            elif method == 'post':
                response = requests.post(url, headers=headers, json=data)
            
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
                logging.error(f"Request failed after {max_retries} attempts. Error: {str(e)}")
                raise
            logging.warning(f"Request failed. Retrying... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)  # Exponential backoff

def add_user_to_org(username, org, role):
    url = f"{GITHUB_API_URL}/orgs/{org}/invitations"
    data = {
        "invitee_id": get_user_id(username),
        "role": role.lower()
    }
    try:
        response = make_request(url, method='post', data=data)
        logging.info(f"Successfully invited {username} to {org} with {role} role")
    except requests.RequestException as e:
        logging.error(f"Failed to invite {username} to {org}. Error: {str(e)}")
        raise

def get_user_id(username):
    url = f"{GITHUB_API_URL}/users/{username}"
    try:
        response = make_request(url)
        return response.json()['id']
    except requests.RequestException as e:
        logging.error(f"Failed to get user ID for {username}. Error: {str(e)}")
        raise

def process_csv(csv_file):
    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip header row
        for row in csv_reader:
            if len(row) == 5:
                mannequin_user, mannequin_id, target_user, role, target = row
                if '/' not in target:  # It's an org
                    try:
                        validate_input(target_user, target, role)
                        add_user_to_org(target_user, target, role)
                    except ValueError as e:
                        logging.error(f"Invalid input: {row}. Error: {str(e)}")
                    except Exception as e:
                        logging.error(f"Unexpected error processing: {row}. Error: {str(e)}")

def main():
    csv_file = os.getenv('CSV_FILE')
    if not csv_file:
        logging.error("CSV_FILE not found. Please set the CSV_FILE environment variable.")
        sys.exit(1)

    process_csv(csv_file)

if __name__ == "__main__":
    main()