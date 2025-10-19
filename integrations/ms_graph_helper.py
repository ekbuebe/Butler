import os
import json
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "Contacts.Read",
    "Tasks.ReadWrite"
]

CACHE_FILE = "token_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def get_access_token():
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    cache = load_cache()
    accounts = app.get_accounts()

    if accounts and "token" in cache:
        return cache["token"]

    # Startet Device Flow (einmalig)
    flow = app.initiate_device_flow(scopes=SCOPES)
    print("👉 Öffne diese Seite und gib den Code ein:")
    print(flow["verification_uri"])
    print("🔑 Code:", flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_cache({"token": result["access_token"]})
        return result["access_token"]
    else:
        raise Exception(result.get("error_description", "Fehler beim Abrufen des Tokens"))

# Beispielabfragen:
def get_mails(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={max_results}"
    res = requests.get(url, headers=headers)
    return res.json().get("value", [])

def get_calendar(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me/events?$top=3"
    res = requests.get(url, headers=headers)
    return res.json().get("value", [])

def get_contacts(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me/contacts?$top=3"
    res = requests.get(url, headers=headers)
    return res.json().get("value", [])

def get_tasks(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me/todo/lists"
    res = requests.get(url, headers=headers)
    return res.json().get("value", [])
