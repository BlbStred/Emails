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
from openai import OpenAI
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





#######################################
# AI SERVICES
#######################################


aiService  = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Return YES, NO, UNSURE depending on AI's classification of the given topic
# topic is typically the subject of an email
def relevance(topic):
    
    try:
        # The Request
        response = aiService.chat.completions.create(
            model="gpt-4o",
            seed=42,         # for determinism
            temperature=0,   # otherwise makes wrong decision with no reason
            messages=[
                {"role"    : "system",
                 "content" : """You are a classifier.
                 Answer 'YES' if the user's text is relevant,
                 answer 'NO' if it is not relevant,
                 answer 'UNSURE' if you are not sure.
                 Provide a brief reason.
                 
                 All social media posts are not relevant,
                 except direct posts by Stephen Edwards (not mere comments on somebody's post).
                 
                 If the text informs me of a new message, searches, job availability, noticing me, or invitation
                 then it is not relevant.               
                 Any news item or public anouncement is not relevant.
                 Any offer of savings or advice is not relevant.
                 Anything designed to draw a person's attention without saying what it is about, is not relevant.
                 
                 Any kind of bank statement is relevant.
                 Anything concerning security is relevant.  
                 """},
                
                {"role": "user",
                 "content": topic}
            ]
        )
        
        result = response.choices[0].message.content
        print(topic, " --> ", result)
        return result.split()[0]  # YES, NO, UNSURE is the first word

    except Exception as e:
        # This catches API errors, connection issues, or encoding bugs
        print(f"*** ERROR *** : {e}")
        return 'UNSURE'

    
    
#######################################
# SOCIAL EMAILS
#######################################

# Format the summary email and send it to myself
def socialEmails(emailList, relevance):

    relevant      = "<p>RELEVANT EMAILS:<br>"
    unsure        = "<p>UNSURE ABOUT:<br>"        
    irrelevant    = "<p>IRRELEVANT EMAILS:<br>"
    numRelevant   = 0
    numIrrelevant = 0
    numUnsure     = 0    
    
    for e in emailList:

        # Prepare the reference link, that will be followed without overtaking the email
        ref = f"""<a href=https://mail.google.com/mail/u/0/#inbox/{e.id} target="_blank" rel="noopener noreferrer">
                {e.id} {e.category}&nbsp;from&nbsp;{e.sender}&nbsp;{e.date}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{e.subject}
                </a><br>
        """

        match relevance(e.subject):
            case 'YES':    relevant += ref; numRelevant   += 1
            case 'NO':   irrelevant += ref; numIrrelevant += 1
            case 'UNSURE': unsure   += ref; numUnsure     += 1                
            case _:        print("*** ERROR *** : Unknown relevance:", relevance(e.subject))

    # Avoid displaying empty lists
    if numRelevant   == 0: relevant   = ""
    if numIrrelevant == 0: irrelevant = ""
    if numUnsure     == 0: unsure     = ""        

    return (
        f"""
        <html>
          <body>
            Received {numRelevant} relevant, {numIrrelevant} irrelevant social emails,
            and unsure about {numUnsure}.
            {relevant}
            {unsure}
            {irrelevant}
            </p>
         </body>
       </html>
       """
      )      


    
#######################################
# COMMON
#######################################

# Format the summary email and send it to myself
def sendEmail(subject, body):

    # Setup the summary email
    msg = MIMEMultipart("alternative")
    msg['From']    = os.environ.get("MY_GMAIL_ADDRESS")
    msg['To']      = os.environ.get("MY_GMAIL_ADDRESS")
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html', 'utf-8'))


    try:
        # --- Connecting to Server ---
        # For Gmail: smtp.gmail.com | Port: 587
        # For Outlook: smtp.office365.com | Port: 587
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(os.environ.get("MY_GMAIL_ADDRESS"),
                     os.environ.get("MY_GMAIL_APP_PASSWORD"))  # App Password, not login password
        server.send_message(msg)
        
    except Exception as e:
        print(f"*** Error *** : {e}")
    
    finally:
        server.quit()




if __name__ == '__main__':

   
    ignore = []
    emails =  getEmailList('', 'yihsin', ignore)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n\n", e, flush=True)
