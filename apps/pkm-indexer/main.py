# main.py

import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
import json

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/drive"]
REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# ─── OAuth2 AUTH FLOW ──────────────────────────────────────────────

@app.get("/auth/initiate")
def auth_initiate():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return RedirectResponse(auth_url)

@app.get("/oauth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"error": "Missing auth code"})

    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(code=code)
    creds = flow.credentials

    with open("token.json", "w") as token_file:
        token_file.write(creds.to_json())

    return {"status": "✅ Authentication successful. token.json saved."}


# ─── MOCK STAGING API (FOR MVP FUNCTIONALITY TEST) ─────────────────

@app.get("/staging")
def get_staging():
    return {"status": "placeholder", "message": "List unprocessed files here"}

@app.post("/approve")
def approve_file(payload: dict):
    return {"status": "approved", "payload": payload}

@app.post("/trigger-organize")
def trigger_organize():
    return {"status": "started", "message": "organize.py would run now"}

# Add file content handlers, Drive sync endpoints, etc. here as needed.
