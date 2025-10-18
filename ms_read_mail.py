import os
import requests
from msal import PublicClientApplication
from dotenv import load_dotenv

# 🔐 ENV laden (.env muss deine MS_CLIENT_ID und MS_TENANT_ID enthalten)
load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default", "https://graph.microsoft.com/Mail.Read"]

def get_access_token():
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    # 1️⃣ Versuch: Token aus Cache
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # 2️⃣ Wenn nicht vorhanden: Interaktiver Login
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

if __name__ == "__main__":
    print("🔐 Hole Outlook-Mailzugriff ...")
    token = get_access_token()
    print("✅ Token erhalten, lade Mails ...")
    get_recent_emails(token)
