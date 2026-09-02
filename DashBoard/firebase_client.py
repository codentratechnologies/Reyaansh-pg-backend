import os
import requests
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
if not DATABASE_URL:
    print("Warning: FIREBASE_DATABASE_URL not found in .env")

# Reusable HTTP Session with connection pooling
http_session = requests.Session()
adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

def sanitize_username(username: str):
    """
    Firebase keys cannot contain '.', '#', '$', '[', or ']'.
    We replace '.' with ',' as is standard practice for emails.
    """
    return username.replace('.', ',')

def get_admin_user(username: str):
    """
    Fetches the admin user from Firebase using the REST API.
    """
    safe_username = sanitize_username(username)
    url = f"{DATABASE_URL}/admin/{safe_username}.json"
    response = http_session.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()
    return None

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

def get_ist_now():
    """Returns current time in Indian Standard Time (IST)"""
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

def create_admin_user(email: str, hashed_password: str):
    """
    Creates or updates an admin user in Firebase using the REST API.
    """
    safe_username = sanitize_username(email)
    
    # Check if user already exists to preserve their ID
    existing_user = get_admin_user(email)
    if existing_user and "admin_id" in existing_user:
        admin_id = existing_user["admin_id"]
    else:
        # Calculate next sequential ID
        url_all = f"{DATABASE_URL}/admin.json"
        try:
            all_admins_resp = http_session.get(url_all, timeout=5)
            all_admins = all_admins_resp.json() or {}
            admin_id = len(all_admins) + 1
        except Exception:
            admin_id = 1
            
    url = f"{DATABASE_URL}/admin/{safe_username}.json"
    
    data = {
        "admin_id": admin_id,
        "email": email,
        "password": hashed_password,
        "is_active": True,
        "last_login": get_ist_now()
    }
    response = http_session.put(url, json=data, timeout=5)
    response.raise_for_status()
    return True

def update_last_login(email: str):
    """
    Updates the last_login field for an admin user in Firebase.
    """
    safe_username = sanitize_username(email)
    url = f"{DATABASE_URL}/admin/{safe_username}.json"
    
    data = {
        "last_login": get_ist_now()
    }
    response = http_session.patch(url, json=data, timeout=5)
    response.raise_for_status()
    return True

def update_admin_profile(email: str, profile_data: dict):
    """
    Updates the admin profile (name, last_name, email, phone_number, location, etc.)
    in Firebase.
    """
    safe_username = sanitize_username(email)
    url = f"{DATABASE_URL}/admin/{safe_username}.json"
    
    response = http_session.patch(url, json=profile_data, timeout=5)
    response.raise_for_status()
    return True
