import requests
import json
from requests.auth import HTTPBasicAuth

api_url = f"http://localhost:80/sessionbot/api/resource/profile/43/"  

# Define the payload with the provided data
payload = {
    "display_name": "SarahClarkxleq",
    "service": "instagram",
    "username": "SarahClarkxleq",
    "password": "Two2uanNucW5Y4U",
    "phone_number": None,
    "email_address": "testo@datatrader.space1",
    "email_password": None,
    "recovery_email": None,
    "imap_email_host": None,
    "imap_email_username": None,
    "imap_email_password": None,
    "imap_email_port": None,
    "followers": 10,
    "following": 20,
    "post_count": 30,
    "profile_picture": None,
    "dob": None,
    "bio": None,
    "first_name": None,
    "last_name": None,
    "created_on": "2024-08-12",
    "cookie": None,
    "state": "active",
    "last_run_at": None
}

# Define headers and authentication
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
auth = HTTPBasicAuth('jeni', 'jeni@123')  # Replace with actual credentials

# Send the PUT request to update the profile
try:
    response = requests.put(api_url, headers=headers, data=json.dumps(payload), auth=auth)
    response.raise_for_status()
    if response.status_code == 200:
        print("Profile updated successfully")
    else:
        print(f"Failed to update profile. Status Code: {response.status_code}. Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
