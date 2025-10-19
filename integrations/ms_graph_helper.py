import os
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Mail.Read", "Calendars.Read", "Contacts.Read", "Tasks.ReadWrite"]

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
    print("👉 Gehe auf https://microsoft.com/devicelogin und gib diesen Code ein:")
    print(flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        return result["access_token"]
    raise Exception(result.get("error_description", "Fehler beim Abrufen des Tokens"))

def get_mails(token, limit=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$orderby=receivedDateTime desc"
    res = requests.get(url, headers=headers).json()
    return [f"📧 {m['subject']} — von {m['from']['emailAddress']['name']}" for m in res.get("value", [])] or ["Keine neuen Mails gefunden."]

def get_events(token, limit=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/events?$top={limit}&$orderby=start/dateTime asc"
    res = requests.get(url, headers=headers).json()
    return [f"📅 {e['subject']} — {e['start']['dateTime']}" for e in res.get("value", [])] or ["Keine Termine gefunden."]

def get_tasks(token, limit=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists"
    res = requests.get(url, headers=headers).json()
    if not res.get("value"):
        return ["Keine Aufgabenlisten gefunden."]
    list_id = res["value"][0]["id"]
    task_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks?$top={limit}"
    tasks = requests.get(task_url, headers=headers).json()
    return [f"✅ {t['title']}" for t in tasks.get("value", [])] or ["Keine Aufgaben gefunden."]
