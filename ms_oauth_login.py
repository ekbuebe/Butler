import os
import webbrowser
from msal import PublicClientApplication
from dotenv import load_dotenv
import requests

load_dotenv()

# Deine App-Infos aus der .env-Datei
CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Mail.Read", "Calendars.ReadWrite", "Tasks.ReadWrite"]

app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

# Öffnet Login-Fenster im Browser
flow = app.initiate_device_flow(scopes=SCOPES)
print(flow["message"])  # Zeigt Code + URL an
webbrowser.open(flow["verification_uri"])

# Benutzer loggt sich manuell ein
result = app.acquire_token_by_device_flow(flow)
if "access_token" in result:
    print("✅ Zugriffstoken erhalten!")
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    res = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    print("🧠 Benutzerinformationen:")
    print(res.json())
else:
    print("❌ Fehler beim Abrufen des Tokens:")
    print(result)
