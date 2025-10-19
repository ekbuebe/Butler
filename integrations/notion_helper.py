# integrations/notion_helper.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# === 📚 Datenbanken abrufen ===
def get_databases():
    """
    Ruft alle Notion-Datenbanken des Nutzers ab.
    """
    url = f"{BASE_URL}/search"
    payload = {"filter": {"property": "object", "value": "database"}}
    res = requests.post(url, headers=HEADERS, json=payload)

    if res.status_code != 200:
        print("❌ Fehler beim Laden der Datenbanken:", res.text)
        return []

    data = res.json()
    return data.get("results", [])


# === 📄 Seiten aus einer Datenbank abrufen ===
def get_pages_in_database(database_id):
    """
    Gibt die ersten Einträge (Seiten) einer Notion-Datenbank zurück.
    """
    url = f"{BASE_URL}/databases/{database_id}/query"
    res = requests.post(url, headers=HEADERS, json={"page_size": 5})

    if res.status_code != 200:
        print("❌ Fehler beim Laden der Seiten:", res.text)
        return []

    data = res.json()
    return data.get("results", [])


# === 📝 Neue Notiz / Seite erstellen ===
def create_page(database_id, title):
    """
    Erstellt eine neue Seite mit Titel in der angegebenen Datenbank.
    """
    url = f"{BASE_URL}/pages"
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": title}}
                ]
            }
        }
    }

    res = requests.post(url, headers=HEADERS, json=payload)

    if res.status_code != 200:
        print("❌ Fehler beim Erstellen der Notion-Seite:", res.text)
        raise Exception(res.text)

    return res.json()
