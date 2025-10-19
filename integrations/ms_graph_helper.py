# integrations/ms_graph_helper.py

import os
import json
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

# === Microsoft App-Konfiguration ===
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

CACHE_FILE = "token_cache.json"


# === Token Cache ===
def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)


# === Zugriffstoken abrufen ===
def get_access_token():
    """
    Versucht zuerst Client-Credentials (Serverlogin),
    und wechselt automatisch auf Device Flow, falls blockiert.
    """
    # --- 1️⃣ Versuch: Client-Credentials ---
    if CLIENT_SECRET:
        data = {
            "client_id": CLIENT_ID,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        }

        res = requests.post(TOKEN_URL, data=data)
        if res.status_code == 200:
            token = res.json().get("access_token")
            if token:
                return token
        else:
            print("⚠️ Client-Credentials fehlgeschlagen – wechsle zu Device Flow ...")
            print("💥 Fehler:", res.text)

    # --- 2️⃣ Versuch: Device Flow (Benutzer-Login) ---
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    cache = _load_cache()

    if "token" in cache:
        print("✅ Verwende gespeichertes Token aus Cache.")
        return cache["token"]

    flow = app.initiate_device_flow(scopes=[
        "User.Read",
        "Mail.Read",
        "Calendars.Read",
        "Contacts.Read",
        "Tasks.ReadWrite",
        "offline_access"
    ])

    if "user_code" not in flow:
        raise Exception("❌ Fehler beim Starten des Device Flow.")

    print("👉 Öffne die Seite https://microsoft.com/devicelogin und gib den Code ein:")
    print("🔑 Code:", flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        _save_cache({"token": result["access_token"]})
        print("✅ Login erfolgreich. Token gespeichert.")
        return result["access_token"]
    else:
        raise Exception(result.get("error_description", "❌ Authentifizierung fehlgeschlagen."))


# === 📧 E-Mails abrufen ===
def get_mails(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/messages?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Mails: {res.text}")

    mails = res.json().get("value", [])
    return [f"📧 {m.get('subject', 'Ohne Betreff')}" for m in mails]


# === 📅 Kalender ===
def get_calendar(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/events?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen des Kalenders: {res.text}")

    events = res.json().get("value", [])
    return [f"📅 {e.get('subject', 'Ohne Titel')}" for e in events]


# === 👤 Kontakte ===
def get_contacts(token, max_results=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/contacts?$top={max_results}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Kontakte: {res.text}")

    contacts = res.json().get("value", [])
    return [f"👤 {c.get('displayName', 'Unbekannt')}" for c in contacts]


# === 📝 Aufgaben ===
def get_tasks(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/todo/lists"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Aufgabenlisten: {res.text}")

    lists = res.json().get("value", [])
    all_tasks = []

    for lst in lists:
        list_id = lst.get("id")
        name = lst.get("displayName", "Ohne Listenname")

        t_url = f"{GRAPH_BASE}/me/todo/lists/{list_id}/tasks"
        t_res = requests.get(t_url, headers=headers)
        if t_res.status_code == 200:
            tasks = t_res.json().get("value", [])
            for t in tasks:
                all_tasks.append(f"📝 {name}: {t.get('title', 'Ohne Titel')}")

    return all_tasks or ["Keine Aufgaben gefunden."]
