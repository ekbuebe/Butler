# integrations/ms_graph_helper.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# === Microsoft App-Konfiguration ===
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# === Token Cache ===
_token_cache = None


def get_access_token():
    """
    Holt ein App-Token über Client Credentials Flow (ohne User Login).
    Perfekt für Server (Render, etc.).
    """
    global _token_cache
    if _token_cache:
        return _token_cache

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }

    res = requests.post(TOKEN_URL, data=data)
    if res.status_code != 200:
        raise Exception(f"❌ Token-Fehler: {res.text}")

    token = res.json().get("access_token")
    _token_cache = token
    return token


# === 📧 E-Mails abrufen ===
def get_mails(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/me/messages?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Mails: {res.text}")

    mails = res.json().get("value", [])
    return [f"📧 {m.get('subject', 'Ohne Betreff')}" for m in mails]


# === 📅 Kalender ===
def get_calendar(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/me/events?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen des Kalenders: {res.text}")

    events = res.json().get("value", [])
    return [f"📅 {e.get('subject', 'Ohne Titel')}" for e in events]


# === 👤 Kontakte ===
def get_contacts(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/me/contacts?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Kontakte: {res.text}")

    contacts = res.json().get("value", [])
    return [f"👤 {c.get('displayName', 'Unbekannt')}" for c in contacts]


# === 📝 Aufgaben ===
def get_tasks(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/me/todo/lists"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Aufgaben: {res.text}")

    lists = res.json().get("value", [])
    all_tasks = []

    for lst in lists:
        list_id = lst.get("id")
        name = lst.get("displayName", "Ohne Listenname")

        task_url = f"{GRAPH_BASE}/users/me/todo/lists/{list_id}/tasks"
        t_res = requests.get(task_url, headers=headers)
        if t_res.status_code == 200:
            tasks = t_res.json().get("value", [])
            for t in tasks:
                all_tasks.append(f"📝 {name}: {t.get('title', 'Ohne Titel')}")

    return all_tasks or ["Keine Aufgaben gefunden."]
