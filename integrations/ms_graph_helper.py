import os
import json
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

# 🔐 ENV laden (.env enthält MS_CLIENT_ID und MS_TENANT_ID)
load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID", "common")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# ⚙️ Scopes – Zugriff auf Mail, Kalender, Kontakte, Aufgaben & Benutzerprofil
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "Contacts.Read",
    "Tasks.ReadWrite"
]

CACHE_FILE = "token_cache.json"

# === Token Cache ===
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

# === Access Token ===
def get_access_token():
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    cache = load_cache()
    accounts = app.get_accounts()

    # Falls Token im Cache vorhanden → direkt verwenden
    if cache.get("token"):
        return cache["token"]

    # Andernfalls Geräte-Flow starten
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("❌ Geräte-Flow konnte nicht gestartet werden.")
    print("\n👉 Öffne die Seite https://microsoft.com/devicelogin und gib den Code ein:")
    print(f"🔑 Code: {flow['user_code']}\n")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_cache({"token": result["access_token"]})
        print("✅ Zugriffstoken gespeichert.")
        return result["access_token"]
    else:
        raise Exception(result.get("error_description", "Fehler beim Abrufen des Tokens"))

# === Outlook Mails ===
def get_mails(token, max_results=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top={max_results}&$orderby=receivedDateTime desc"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return [f"❌ Fehler beim Abrufen der Mails: {res.text}"]
    mails = res.json().get("value", [])
    return [
        f"📧 {m.get('subject', 'Kein Betreff')} — {m.get('from', {}).get('emailAddress', {}).get('address', 'Unbekannt')}"
        for m in mails
    ] or ["Keine Mails gefunden."]

# === Kalender ===
def get_calendar(token, max_results=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/events?$top={max_results}&$orderby=start/dateTime desc"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return [f"❌ Fehler beim Abrufen der Termine: {res.text}"]
    events = res.json().get("value", [])
    return [
        f"📅 {e.get('subject', 'Kein Titel')} — {e.get('start', {}).get('dateTime', 'Kein Datum')}"
        for e in events
    ] or ["Keine Termine gefunden."]

# === Kontakte ===
def get_contacts(token, max_results=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/contacts?$top={max_results}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return [f"❌ Fehler beim Abrufen der Kontakte: {res.text}"]
    contacts = res.json().get("value", [])
    return [
        f"👤 {c.get('displayName', 'Unbekannt')} ({c.get('emailAddresses', [{}])[0].get('address', '-')})"
        for c in contacts
    ] or ["Keine Kontakte gefunden."]

# === Aufgaben (Microsoft To Do) ===
def get_tasks(token, max_results=5):
    headers = {"Authorization": f"Bearer {token}"}
    lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
    res = requests.get(lists_url, headers=headers)
    if res.status_code != 200:
        return [f"❌ Fehler beim Abrufen der Aufgabenlisten: {res.text}"]
    lists = res.json().get("value", [])
    if not lists:
        return ["Keine Aufgabenlisten gefunden."]
    
    list_id = lists[0]["id"]
    tasks_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks?$top={max_results}"
    tasks_res = requests.get(tasks_url, headers=headers)
    if tasks_res.status_code != 200:
        return [f"❌ Fehler beim Abrufen der Aufgaben: {tasks_res.text}"]
    tasks = tasks_res.json().get("value", [])
    return [
        f"📝 {t.get('title', 'Unbenannte Aufgabe')}"
        for t in tasks
    ] or ["Keine Aufgaben gefunden."]
