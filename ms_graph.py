import os
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = os.getenv("MS_SCOPES", "User.Read Mail.Read Contacts.Read Calendars.Read Tasks.ReadWrite").split()

def get_access_token():
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

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

def get_mails(token, top=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top={top}&$orderby=receivedDateTime desc"
    res = requests.get(url, headers=headers).json()
    return [f"📧 {m['subject']} — {m['from']['emailAddress']['address']}" for m in res.get("value", [])]

def get_calendar_events(token, top=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/events?$top={top}&$orderby=start/dateTime"
    res = requests.get(url, headers=headers).json()
    return [f"📅 {e['subject']} — {e['start']['dateTime']}" for e in res.get("value", [])]

def get_contacts(token, top=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/contacts?$top={top}"
    res = requests.get(url, headers=headers).json()
    return [f"👤 {c['displayName']} — {c.get('emailAddresses',[{'address':'-'}])[0]['address']}" for c in res.get("value", [])]

def get_tasks(token, top=5):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists"
    lists = requests.get(url, headers=headers).json().get("value", [])
    if not lists:
        return ["📝 Keine Aufgabenlisten gefunden."]
    list_id = lists[0]["id"]
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks?$top={top}"
    res = requests.get(url, headers=headers).json()
    return [f"☑️ {t['title']}" for t in res.get("value", [])]
