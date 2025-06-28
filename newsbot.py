import json, os, datetime, sendgrid, openai, requests, pytz
from sendgrid.helpers.mail import Mail
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load secrets
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FILE_ID        = os.getenv("FILE_ID")
SUBSTACK_ADDR  = os.getenv("SUBSTACK_IN_ADDR")
SG_KEY         = os.getenv("SENDGRID_KEY")

openai.api_key = OPENAI_API_KEY
sg = sendgrid.SendGridAPIClient(SG_KEY)

# 1. grab today’s doc
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.getenv("GOOGLE_SERVICE_JSON")),
    scopes=["https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly"],
)
docs = build("docs", "v1", credentials=creds)
raw = docs.documents().get(documentId=FILE_ID).execute()
body = "\n".join(elem.get("paragraph").get("elements")[0]
                 .get("textRun").get("content", "")
                 for elem in raw["body"]["content"]
                 if "paragraph" in elem)

# 2. hand off to assistant
assistant_prompt = f"""
You are an experienced trade-press editor writing a daily, no-nonsense briefing
for grocery-CPG executives. Write in the style shown below.

TONE EXAMPLE:
June 26 — the sun comes up to ...

SOURCE TEXT (one article per block):
{body}
"""

resp = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": assistant_prompt}],
)
newsletter_md = resp.choices[0].message.content

# 3. e-mail to Substack
today = datetime.datetime.now(pytz.timezone("America/Chicago")).strftime("%Y-%m-%d")
message = Mail(
    from_email="bot@yourdomain.com",
    to_emails=SUBSTACK_ADDR,
    subject=f"🛒 CPG Daily Brief — {today}",
    plain_text_content=newsletter_md,
)
sg.send(message)
