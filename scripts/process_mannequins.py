import os
import sys
import csv
import logging
import requests
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_API_URL = "https://api.github.com"
TOKEN = os.getenv('GITHUB_TOKEN')
CSV_FILE = os.getenv('CSV_FILE')
AD_API_URL = os.getenv('AD_API_URL')  # You need to set this to your Active Directory API endpoint

def get_ad_email(username):
    # This function should query your Active Directory API to get the email for a given username
    # Implement the actual API call based on your AD setup
    response = requests.get(f"{AD_API_URL}/users/{username}")
    if response.status_code == 200:
        return response.json().get('email')
    return None

def determine_role(mannequin_role):
    # Map mannequin roles to GitHub roles/permissions
    role_mapping = {
        'Admin': 'admin',
        'Write': 'push',
        'Read': 'pull',
        # Add more mappings as needed
    }
    return role_mapping.get(mannequin_role, 'pull')  # Default to 'pull' if role is not recognized

def add_user_to_org(username, org, role):
    url = f"{GITHUB_API_URL}/orgs/{org}/invitations"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "invitee_id": get_user_id(username),
        "role": role.lower()
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info(f"Successfully invited {username} to {org} with {role} role")
    else:
        logging.error(f"Failed to invite {username} to {org}. Status code: {response.status_code}")

def add_user_to_repo(username, repo, permission):
    owner, repo_name = repo.split('/')
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/collaborators/{username}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"permission": permission.lower()}
    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info(f"Successfully added {username} to {repo} with {permission} permission")
    else:
        logging.error(f"Failed to add {username} to {repo}. Status code: {response.status_code}")

def get_user_id(username):
    url = f"{GITHUB_API_URL}/users/{username}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['id']
    else:
        logging.error(f"Failed to get user ID for {username}. Status code: {response.status_code}")
        return None

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
            target = row['target']
            mannequin_role = row['role']

            # Get the AD email for the mannequin user
            ad_email = get_ad_email(mannequin_username)
            if not ad_email:
                logging.error(f"Could not find AD email for {mannequin_username}")
                continue

            # Determine the appropriate role/permission
            github_role = determine_role(mannequin_role)

            # Add user to org or repo based on the target
            if '/' in target:  # It's a repo
                add_user_to_repo(ad_email, target, github_role)
            else:  # It's an org
                add_user_to_org(ad_email, target, github_role)

def main():
    if not TOKEN:
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

if __name__ == "__main__":
    main()