import os
import sys
import csv
import logging
import requests
import time

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

def validate_input(username, target, role):
    valid_roles = ['admin', 'member', 'owner', 'pull', 'push', 'admin']
    if not username or not target or not role:
        raise ValueError("Username, target, and role must be provided")
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

def add_user_to_repo(username, repo, permission):
    url = f"{GITHUB_API_URL}/repos/{repo}/collaborators/{username}"
    data = {"permission": permission.lower()}
    try:
        response = make_request(url, method='put', data=data)
        logging.info(f"Successfully added {username} to {repo} with {permission} permission")
    except requests.RequestException as e:
        logging.error(f"Failed to add {username} to {repo}. Error: {str(e)}")

def get_user_id(username):
    url = f"{GITHUB_API_URL}/users/{username}"
    try:
        response = make_request(url)
        return response.json()['id']
    except requests.RequestException as e:
        logging.error(f"Failed to get user ID for {username}. Error: {str(e)}")
        raise

def validate_csv(csv_file):
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    
    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader, None)
        if header != ['mannequin_username', 'mannequin_id', 'role', 'target']:
            raise ValueError("CSV file does not have the correct header format")

def process_mannequins(csv_file):
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            mannequin_username = row['mannequin_username']
            target_user = row['mannequin_id']  # Using mannequin_id as target_user
            role = row['role']
            target = row['target']

            try:
                validate_input(target_user, target, role)
                if '/' in target:  # It's a repo
                    add_user_to_repo(target_user, target, role)
                else:  # It's an org
                    add_user_to_org(target_user, target, role)
            except ValueError as e:
                logging.error(f"Invalid input: {row}. Error: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error processing: {row}. Error: {str(e)}")

def main():
    try:
        validate_csv(CSV_FILE)
        process_mannequins(CSV_FILE)
    except (FileNotFoundError, ValueError) as e:
        logging.error(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()