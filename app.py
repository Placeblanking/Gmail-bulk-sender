import streamlit as st
import base64
import mimetypes
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Page config
st.set_page_config(page_title="📧 Gmail Bulk Sender", layout="centered")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# === Gmail Service ===
def gmail_service():
    """Authenticate Gmail using refresh token from Streamlit secrets or local secrets.toml"""
    try:
        gmail_secrets = st.secrets["gmail"]
    except KeyError:
        st.error("⚠️ Gmail secrets not found! Add them in Streamlit Cloud secrets or .streamlit/secrets.toml")
        st.stop()

    creds = Credentials(
        None,
        refresh_token=gmail_secrets["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=gmail_secrets["client_id"],
        client_secret=gmail_secrets["client_secret"],
        scopes=SCOPES,
    )

    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)

# === Send Email Function ===
def send_message(service, sender, to, subject, body, attachments=None):
    """Send an email with optional attachments"""
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    if attachments:
        for file in attachments:
            try:
                file.seek(0)  # reset pointer
                content_type, encoding = mimetypes.guess_type(file.name)
                if content_type is None or encoding is not None:
                    content_type = "application/octet-stream"
                main_type, sub_type = content_type.split("/", 1)

                mime = MIMEBase(main_type, sub_type)
                mime.set_payload(file.read())
                encoders.encode_base64(mime)
                mime.add_header("Content-Disposition", "attachment", filename=file.name)
                message.attach(mime)
            except Exception as e:
                st.warning(f"⚠️ Failed to attach {file.name}: {e}")

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()

# === Streamlit UI ===
st.title("📧 Gmail Bulk Sender")
st.write("Send the same email to multiple recipients with attachments.")

sender = st.text_input("Sender Email", placeholder="your_email@gmail.com")
recipients = st.text_area("Recipients (comma separated)", placeholder="user1@gmail.com, user2@gmail.com")
subject = st.text_input("Subject")
body = st.text_area("Message Body")
attachments = st.file_uploader("Attachments", type=None, accept_multiple_files=True)

if st.button("Send Emails"):
    if not sender or not recipients or not subject or not body:
        st.error("⚠️ Please fill all fields before sending.")
    else:
        service = gmail_service()
        rec_list = [r.strip() for r in recipients.split(",") if r.strip()]
        results = []

        with st.spinner("Sending emails..."):
            for r in rec_list:
                try:
                    result = send_message(service, sender, r, subject, body, attachments)
                    results.append((r, "✅ Sent", result["id"]))
                except Exception as e:
                    results.append((r, "❌ Failed", str(e)))

        st.subheader("Results")
        for r, status, info in results:
            st.write(f"{status} to {r}: {info}")
