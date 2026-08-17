# When gmail autorization expires:
#
# 1 regenerate token.json
# 1.1 delete token.json
# 1.2 python SocialEmailsAgent.py
# 1.3 Google will open a warning window
# 1.4 Do not go to safety -- click on "advanced"
# 1.5 Do what they label as unsafe
#
# 2. regenerate MY_GMAIL_APP_PASSWORD in .env
# 2.1 go to myaccount.google.com/apppasswords





import re
import os.path
import sys
from dotenv import load_dotenv # run 'pip install python-dotenv'
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import EmailMessage
import GmailService

# Load environment variables from .env
load_dotenv()

# Reconfigure stdout to handle errors gracefully
sys.stdout.reconfigure(errors='replace')



#######################################
# GMAIL SERVICES
#######################################
        


s = GmailService.GmailService()
gmailService = s.service() # To access gmail



import base64



def get_message_body(payload):
    """
    Extracts text/plain or text/html body from a full Gmail API message object.
    Returns a dict: {'plain': str, 'html': str}
    """
    
    bodies = {'plain': '', 'html': ''}

    def parse_parts(parts):
        
        for part in parts:
            mime_type = part.get('mimeType')
            body_data = part.get('body', {}).get('data')

            if body_data:
                # Gmail API uses URL-safe base64 encoding (- and _ instead of + and /)
                decoded_bytes = base64.urlsafe_b64decode(body_data)
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')

                if mime_type == 'text/plain' and not bodies['plain']:
                    bodies['plain'] = decoded_text
                elif mime_type == 'text/html' and not bodies['html']:
                    bodies['html'] = decoded_text

            # Recursively handle nested multi-part structures
            if 'parts' in part:
                parse_parts(part['parts'])

    # 1. Simple Single-Part Message
    
    if 'data' in payload.get('body', {}):
        body_data = payload['body']['data']
        decoded_bytes = base64.urlsafe_b64decode(body_data)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        
        mime_type = payload.get('mimeType', 'text/plain')
        if mime_type == 'text/html':
            bodies['html'] = decoded_text
        else:
            bodies['plain'] = decoded_text

    # 2. Multi-Part Message (e.g., multipart/alternative, multipart/mixed)
    elif 'parts' in payload:
        parse_parts(payload['parts'])

    return bodies


def getEmailList(category, label, ignoreIdList):
    messages = s.emailList(category, label)
    
    emailList = []          # the list to return
    for msg in messages:
        # Check whether precessed previously
        msgId = msg['id']
        
                
        # msg provides id only, fetch full message details
        message = gmailService.users().messages().get(userId='me', id=msgId).execute()
        
        # Extract headers 
        payload = message.get('payload', {})
        headers = payload.get('headers', [])

        body = get_message_body(payload)['plain']
        
        # headers is a list of dictionaries {'name: ..., 'value': ...}
        # To get the subject, for example, find the first dictionary {'name: 'Subject', 'value': ...}
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'),    'Unknown Sender')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'),    'Unknown Date')
        date    = re.split(r'[+-]', date)[0]     # Get rid of the universal time at the end

        emailList.append(EmailMessage.EmailMessage(msgId, sender, subject, date, category, body))

    return emailList



    
    
if __name__ == '__main__':

   
    ignore = []
    emails =  getEmailList('', 'yihsin', ignore)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n\n", e, flush=True)
