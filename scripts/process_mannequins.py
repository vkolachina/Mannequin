import os
import sys
import csv
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
CSV_FILE = os.getenv('CSV_FILE')

def determine_role(mannequin_role):
    # Map mannequin roles to GitHub roles/permissions
    role_mapping = {
        'Admin': 'admin',
        'Write': 'push',
        'Read': 'pull',
    }
    return role_mapping.get(mannequin_role, 'pull')  # Default to 'pull' if role is not recognized

def add_user_to_org(target_id, org, role):
    url = f"{GITHUB_API_URL}/orgs/{org}/invitations"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "invitee_id": target_id,
        "role": role.lower()
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info(f"Successfully invited user with ID {target_id} to {org} with {role} role")
    else:
        logging.error(f"Failed to invite user with ID {target_id} to {org}. Status code: {response.status_code}")

def add_user_to_repo(target_id, repo, permission):
    owner, repo_name = repo.split('/')
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/collaborators/{target_id}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"permission": permission.lower()}
    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info(f"Successfully added user with ID {target_id} to {repo} with {permission} permission")
    else:
        logging.error(f"Failed to add user with ID {target_id} to {repo}. Status code: {response.status_code}")

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

            # Determine the appropriate role/permission
            github_role = determine_role(role)

            # Add user to org or repo based on the target
            if '/' in target:  # It's a repo
                add_user_to_repo(mannequin_id, target, github_role)
            else:  # It's an org
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

if __name__ == "__main__":
    main()