import os
import base64
import mimetypes
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def gmail_authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def send_message(service, sender, to, subject, body, attachments=None):
    """Send email with optional multiple attachments"""
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    if attachments:
        for attachment in attachments:
            content_type, encoding = mimetypes.guess_type(attachment)
            if content_type is None or encoding is not None:
                content_type = "application/octet-stream"
            main_type, sub_type = content_type.split("/", 1)

            with open(attachment, "rb") as f:
                mime = MIMEBase(main_type, sub_type)
                mime.set_payload(f.read())
                encoders.encode_base64(mime)

            filename = os.path.basename(attachment)
            mime.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(mime)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ======================
# STREAMLIT UI
# ======================
st.set_page_config(page_title="Simple Gmail Bulk Sender", layout="centered")
st.title("📧 Simple Gmail Bulk Sender")

st.sidebar.header("Sender Details")
sender_email = st.sidebar.text_input("Your Gmail", "your_email@gmail.com")

st.header("Compose Email")

recipients = st.text_area("Recipients (comma or semicolon separated)", 
                          "test1@gmail.com, test2@gmail.com")

subject = st.text_input("Subject")
body = st.text_area("Message Body")

uploaded_files = st.file_uploader("Attachments (optional)", accept_multiple_files=True)

if st.button("Send Email"):
    if not recipients.strip():
        st.error("❌ Please enter at least one recipient email.")
    else:
        service = gmail_authenticate()
        recipients_list = [r.strip() for r in recipients.replace(";", ",").split(",") if r.strip()]

        # Save uploaded files temporarily
        temp_files = []
        if uploaded_files:
            for f in uploaded_files:
                temp_path = os.path.join("temp_" + f.name)
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(f.getbuffer())
                temp_files.append(temp_path)

        success_count, fail_count = 0, 0
        for recipient in recipients_list:
            try:
                result = send_message(
                    service,
                    sender=sender_email,
                    to=recipient,
                    subject=subject,
                    body=body,
                    attachments=temp_files
                )
                success_count += 1
                st.success(f"✅ Sent to {recipient} (Message ID: {result['id']})")
            except Exception as e:
                fail_count += 1
                st.error(f"❌ Failed to send to {recipient}: {e}")

        # Cleanup
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

        st.info(f"📊 Summary: {success_count} sent, {fail_count} failed.")
