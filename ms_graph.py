import os
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

# 🔐 ENV laden (.env muss deine MS_CLIENT_ID und MS_TENANT_ID enthalten)
load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# 👉 Scopes für alle Microsoft-Dienste, die du brauchst
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "Contacts.Read",
    "Tasks.ReadWrite",
]

def get_access_token():
    """Startet den Geräte-Flow und gibt das Access Token zurück"""
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    # 1️⃣ Versuche, gespeichertes Token zu nutzen
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # 2️⃣ Wenn kein Token vorhanden → interaktiver Geräte-Login
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("Geräte-Flow konnte nicht gestartet werden.")
    print("👉 Öffne diese Seite und gib den Code ein:")
    print(flow["verification_uri"])
    print("🔑 Code:", flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(result.get("error_description", "Fehler beim Abrufen des Tokens"))


def get_recent_emails(access_token, max_results=5):
    """📧 Holt die letzten E-Mails aus dem Posteingang"""
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top={max_results}&$orderby=receivedDateTime desc"

    res = requests.get(endpoint, headers=headers)
    if res.status_code != 200:
        print("❌ Fehler beim Abrufen der Mails:", res.json())
        return []

    mails = res.json().get("value", [])
    for i, mail in enumerate(mails, start=1):
        print(f"\n📧 {i}. {mail['subject']}")
        print(f"   Von: {mail.get('from', {}).get('emailAddress', {}).get('address', 'Unbekannt')}")
        print(f"   Erhalten am: {mail['receivedDateTime']}")
    return mails


def get_calendar_events(access_token, max_results=5):
    """📅 Holt bevorstehende Kalenderereignisse"""
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = f"https://graph.microsoft.com/v1.0/me/events?$top={max_results}&$orderby=start/dateTime asc"

    res = requests.get(endpoint, headers=headers)
    if res.status_code != 200:
        print("❌ Fehler beim Abrufen der Kalenderdaten:", res.json())
        return []

    events = res.json().get("value", [])
    for i, ev in enumerate(events, start=1):
        print(f"\n📅 {i}. {ev['subject']}")
        print(f"   Start: {ev['start']['dateTime']} ({ev['start']['timeZone']})")
        print(f"   Ende:  {ev['end']['dateTime']} ({ev['end']['timeZone']})")
    return events


def get_contacts(access_token, max_results=5):
    """📇 Holt gespeicherte Kontakte"""
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = f"https://graph.microsoft.com/v1.0/me/contacts?$top={max_results}"

    res = requests.get(endpoint, headers=headers)
    if res.status_code != 200:
        print("❌ Fehler beim Abrufen der Kontakte:", res.json())
        return []

    contacts = res.json().get("value", [])
    for i, c in enumerate(contacts, start=1):
        print(f"\n📇 {i}. {c.get('displayName', 'Ohne Namen')}")
        print(f"   E-Mail: {c.get('emailAddresses', [{}])[0].get('address', 'Keine')}")
    return contacts


def get_tasks(access_token, max_results=5):
    """✅ Holt To-Do-Aufgaben"""
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = "https://graph.microsoft.com/v1.0/me/todo/lists"

    lists_res = requests.get(endpoint, headers=headers)
    if lists_res.status_code != 200:
        print("❌ Fehler beim Abrufen der Aufgabenlisten:", lists_res.json())
        return []

    lists = lists_res.json().get("value", [])
    if not lists:
        print("⚠️ Keine Aufgabenlisten gefunden.")
        return []

    list_id = lists[0]["id"]
    tasks_res = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks?$top={max_results}", headers=headers)
    if tasks_res.status_code != 200:
        print("❌ Fehler beim Abrufen der Aufgaben:", tasks_res.json())
        return []

    tasks = tasks_res.json().get("value", [])
    for i, t in enumerate(tasks, start=1):
        print(f"\n✅ {i}. {t['title']}")
        print(f"   Status: {t['status']}")
    return tasks


if __name__ == "__main__":
    print("🔐 Starte Microsoft Graph Zugriff ...")
    token = get_access_token()
    print("✅ Zugriff erfolgreich! Daten werden geladen ...")

    get_recent_emails(token)
    get_calendar_events(token)
    get_contacts(token)
    get_tasks(token)
