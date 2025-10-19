import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv
from integrations.ms_graph_helper import (
    get_access_token,
    get_mails,
    get_calendar,
    get_contacts,
    get_tasks
)

# === ENV laden ===
load_dotenv()

app = Flask(__name__)

# === Clients & Keys ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# === Hilfsfunktion für WhatsApp-Antwort ===
def _twilio_response(message: str):
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)

# === Notion: Neue Notiz anlegen ===
def create_notion_page(content: str):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": content[:100]}}]}
        },
        "children": [
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": content}}]}}
        ]
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        return "✅ Notiz wurde in Notion gespeichert!"
    else:
        print("❌ Notion API Fehler:", res.text)
        return "⚠️ Fehler beim Speichern in Notion."

# === Notion: Letzte Notizen abrufen ===
def get_notion_notes(limit=3):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    res = requests.post(url, headers=headers)
    if res.status_code != 200:
        print("❌ Notion Fehler:", res.text)
        return ["Fehler beim Laden der Notizen."]
    data = res.json().get("results", [])
    notes = []
    for page in data[:limit]:
        title = page["properties"].get("Name", {}).get("title", [])
        title_text = title[0]["text"]["content"] if title else "Ohne Titel"
        notes.append(f"📝 {title_text}")
    return notes or ["Keine Notizen gefunden."]

# === Haupt-Webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()
        reply_text = ""

        # 🎙️ Sprachdatei
        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
            if audio_response.status_code == 200:
                with open("voice.ogg", "wb") as f:
                    f.write(audio_response.content)
                os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')
                with open("voice.wav", "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                incoming_text = transcription.text
                os.remove("voice.ogg")
                os.remove("voice.wav")

        if not incoming_text:
            return _twilio_response("Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib nochmal.")
        lower_text = incoming_text.lower()

        # === Microsoft Graph Abfragen ===
        if "mail" in lower_text or "nachricht" in lower_text:
            token = get_access_token()
            mails = get_mails(token)
            reply_text = "\n".join([f"📧 {m.get('subject', 'Ohne Betreff')}" for m in mails]) or "Keine Mails gefunden."

        elif "kalender" in lower_text or "termin" in lower_text:
            token = get_access_token()
            events = get_calendar(token)
            reply_text = "\n".join([f"📅 {e.get('subject', 'Ohne Titel')}" for e in events]) or "Keine Termine gefunden."

        elif "kontakt" in lower_text or "kontakte" in lower_text:
            token = get_access_token()
            contacts = get_contacts(token)
            reply_text = "\n".join([f"👤 {c.get('displayName', 'Unbekannt')}" for c in contacts]) or "Keine Kontakte gefunden."

        elif "aufgabe" in lower_text or "to-do" in lower_text:
            token = get_access_token()
            tasks = get_tasks(token)
            reply_text = "\n".join([f"📝 {t.get('displayName', 'Unbenannte Aufgabe')}" for t in tasks]) or "Keine Aufgaben gefunden."

        # === Notion Befehle ===
        elif "notion" in lower_text and "neue" in lower_text:
            note_text = incoming_text.split("notion", 1)[-1].replace("neue", "").strip()
            reply_text = create_notion_page(note_text)

        elif "notion" in lower_text and ("zeige" in lower_text or "liste" in lower_text):
            notes = get_notion_notes()
            reply_text = "\n".join(notes)

        else:
            # 💬 GPT Chat
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": incoming_text}]
            )
            reply_text = response.choices[0].message.content.strip()

        return _twilio_response(reply_text)

    except Exception as e:
        print("💥 Fehler:", e)
        return _twilio_response("🚨 Unerwarteter Fehler. Bitte versuch es später erneut.")

# === Start ===
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
