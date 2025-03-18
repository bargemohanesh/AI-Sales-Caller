#!/usr/bin/env python
# coding: utf-8

# # AI_Sales_Caller.

# In[ ]:


from flask import Flask, request, jsonify, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
import logging
import dateparser
import os
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Used for session security

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Twilio Credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)

# Google Calendar API Setup
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE")

def authenticate_google():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)

calendar_service = authenticate_google()

@app.route("/")
def home():
    return "Hello, AI Sales Caller is Running!"

# 📞 Make a Twilio Call
@app.route("/call", methods=["GET"])
def make_call():
    to = "+918275760425"
    try:
        call = client.calls.create(
            twiml=f'''<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Gather input="speech" action="/process" method="POST" timeout="5">
                    <Say>Hello, this is your AI Sales Assistant! Would you like to know about our courses or book a demo?</Say>
                </Gather>
                <Say>Sorry, I didn't hear anything. Goodbye.</Say>
            </Response>''',
            to=to,
            from_=twilio_number,
        )
        logging.info(f"✅ Call initiated with SID: {call.sid}")
        return jsonify({"message": "Call placed successfully!", "call_sid": call.sid})
    except Exception as e:
        logging.error(f"❌ Error initiating call: {e}")
        return jsonify({"error": str(e)}), 500

# 🧠 Process Speech from Twilio
@app.route("/process", methods=["POST"])
def process_speech():
    user_input = request.form.get("SpeechResult", "").strip().lower()
    logging.info(f"🎤 User said: {user_input}")

    response = VoiceResponse()

    if "course" in user_input:
        ai_response = "We offer comprehensive data science and AI courses. Would you like to know the curriculum details?"
    elif "demo" in user_input or "schedule" in user_input or "book" in user_input:
        ai_response = "I can schedule a demo for you. Please say a suitable date and time."
        response.say(ai_response)
        gather = Gather(input="speech", action="/process_date", method="POST", timeout="5")
        response.append(gather)
    else:
        ai_response = "I'm sorry, I didn't understand that."
        gather = Gather(input="speech", action="/process", method="POST", timeout="5")
        response.say(ai_response)
        response.append(gather)
        return str(response)
    
    response.say(ai_response)
    return str(response)

# 📅 Process Date & Schedule Google Meet
@app.route("/process_date", methods=["POST"])
def process_date():
    user_input = request.form.get("SpeechResult", "").strip().lower()
    logging.info(f"🎤 User said (date attempt): {user_input}")

    response = VoiceResponse()
    date_time = dateparser.parse(user_input)

    if date_time:
        slot = date_time.strftime("%Y-%m-%dT%H:%M:%S")
        meeting_link = schedule_google_meet(slot)
        ai_response = f"Your demo has been scheduled. Here is your Google Meet link: {meeting_link}"
        sms_body = f"Your demo is scheduled. Join here: {meeting_link}"
        to = "+918275760425"
        client.messages.create(body=sms_body, from_=twilio_number, to=to)
    else:
        ai_response = "I couldn't understand the date and time. Please repeat it clearly."
        response.say(ai_response)
        response.redirect("/process")  

    response.say(ai_response)
    return str(response)

# 🗓️ Schedule Google Meet
def schedule_google_meet(slot):
    event = {
        "summary": "AI Sales Caller Demo Meeting",
        "description": "This is a demo meeting scheduled by AI Sales Caller.",
        "start": {"dateTime": slot, "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": slot, "timeZone": "Asia/Kolkata"},
        "conferenceData": {
            "createRequest": {
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
                "requestId": "random-1234"
            }
        }
    }
    event = calendar_service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1
    ).execute()

    return event["hangoutLink"]

# 📞 Voice Call Verification (For Testing)
@app.route('/voice', methods=['GET'])
def voice():
    return Response('''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say>Hello! Your AI Sales Agent is active.</Say>
    </Response>''', mimetype='text/xml')

if __name__ == "__main__":
    logging.info("🚀 Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)


# In[ ]:




