import os
import sys
import csv
import logging
import requests
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
CSV_FILE = os.getenv('CSV_FILE')

def determine_role(mannequin_role):
    role_mapping = {
        'Admin': 'admin',
        'Write': 'push',
        'Read': 'pull',
    }
    return role_mapping.get(mannequin_role, 'pull')

def make_github_request(url, method='POST', data=None):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        if method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        if response:
            logging.error(f"Response content: {response.text}")
        return None

def add_user_to_org(target_id, org, role):
    url = f"{GITHUB_API_URL}/orgs/{org}/invitations"
    data = {
        "invitee_id": int(target_id),
        "role": role.lower()
    }
    response = make_github_request(url, method='POST', data=data)
    if response and response.status_code == 201:
        logging.info(f"Successfully invited user with ID {target_id} to {org} with {role} role")
    elif response:
        error_data = json.loads(response.text)
        logging.error(f"Failed to invite user with ID {target_id} to {org}. Status code: {response.status_code}")
        logging.error(f"Error message: {error_data.get('message', 'Unknown error')}")
        for error in error_data.get('errors', []):
            logging.error(f"Error detail: {error}")

def add_user_to_repo(target_id, repo, permission):
    owner, repo_name = repo.split('/')
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/collaborators/{target_id}"
    data = {"permission": permission.lower()}
    response = make_github_request(url, method='PUT', data=data)
    if response and response.status_code == 201:
        logging.info(f"Successfully added user with ID {target_id} to {repo} with {permission} permission")
    elif response:
        error_data = json.loads(response.text)
        logging.error(f"Failed to add user with ID {target_id} to {repo}. Status code: {response.status_code}")
        logging.error(f"Error message: {error_data.get('message', 'Unknown error')}")
        for error in error_data.get('errors', []):
            logging.error(f"Error detail: {error}")

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
            mannequin_id = row['mannequin_id']
            role = row['role']
            target = row['target']

            github_role = determine_role(role)

            logging.info(f"Processing user: {mannequin_username} (ID: {mannequin_id})")
            if '/' in target:
                add_user_to_repo(mannequin_id, target, github_role)
            else:
                add_user_to_org(mannequin_id, target, github_role)

def main():
    if not GITHUB_TOKEN:
        logging.error("GITHUB_TOKEN not found. Please set the GITHUB_TOKEN environment variable.")
        sys.exit(1)

    if not CSV_FILE:
        logging.error("CSV_FILE not found. Please set the CSV_FILE environment variable.")
        sys.exit(1)

    try:
        validate_csv(CSV_FILE)
        process_mannequins(CSV_FILE)
    except (FileNotFoundError, ValueError) as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()