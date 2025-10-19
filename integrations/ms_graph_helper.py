# integrations/ms_graph_helper.py

import os
import json
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CACHE_FILE = "token_cache.json"

# Nur sichere Scopes
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "Contacts.Read",
    "Tasks.ReadWrite"
]

def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def get_access_token():
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    cache = _load_cache()

    # Cached Token wiederverwenden
    if "token" in cache:
        return cache["token"]

    # Device Flow starten
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("❌ Device Flow konnte nicht gestartet werden.")

    print("👉 Öffne diese Seite und gib den Code ein:")
    print(flow["verification_uri"])
    print("🔑 Code:", flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        _save_cache({"token": result["access_token"]})
        print("✅ Token erfolgreich gespeichert.")
        return result["access_token"]
    else:
        raise Exception(result.get("error_description", "❌ Fehler beim Abrufen des Tokens."))

# === Funktionen für Mail, Kalender, Kontakte, Aufgaben ===

def get_mails(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/messages?$top={max_results}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.text)
    return [f"📧 {m.get('subject', 'Ohne Betreff')}" for m in res.json().get("value", [])]

def get_calendar(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/events?$top={max_results}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.text)
    return [f"📅 {e.get('subject', 'Ohne Titel')}" for e in res.json().get("value", [])]

def get_contacts(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/contacts?$top={max_results}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.text)
    return [f"👤 {c.get('displayName', 'Unbekannt')}" for c in res.json().get("value", [])]

def get_tasks(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/todo/lists"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.text)
    lists = res.json().get("value", [])
    all_tasks = []
    for lst in lists:
        list_id = lst["id"]
        list_name = lst.get("displayName", "Ohne Listenname")
        t_res = requests.get(f"{GRAPH_BASE}/me/todo/lists/{list_id}/tasks", headers=headers)
        if t_res.status_code == 200:
            for t in t_res.json().get("value", []):
                all_tasks.append(f"📝 {list_name}: {t.get('title', 'Ohne Titel')}")
    return all_tasks or ["Keine Aufgaben gefunden."]
