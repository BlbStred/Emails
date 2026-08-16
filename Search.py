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




import os
import re
import os.path
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI
from dotenv import load_dotenv # run 'pip install python-dotenv'
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env
load_dotenv()

# Reconfigure stdout to handle errors gracefully
sys.stdout.reconfigure(errors='replace')



#######################################
# GMAIL SERVICES
#######################################
        

def get_gmail_service():
    
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)



gmailService = get_gmail_service() # To access gmail





def getEmailList(category, ignoreIdList):
    
    # List messages (Gmail returns these in reverse chronological order by default)
    results = gmailService.users().messages().list(userId='me',
                                                   q=f"label:yihsin").execute()
    messages = results.get('messages', [])
    print(len(messages), "messages")
    
    emailList = []          # the list to return
    for msg in messages:
        # Check whether precessed previously
        msgId = msg['id']

                
        # msg provides id only, fetch full message details
        message = gmailService.users().messages().get(userId='me', id=msgId).execute()
        
        # Extract headers 
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # headers is a list of dictionaries {'name: ..., 'value': ...}
        # To get the subject, for example, find the first dictionary {'name: 'Subject', 'value': ...}
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'),    'Unknown Sender')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'),    'Unknown Date')
        date    = re.split(r'[+-]', date)[0]     # Get rid of the universal time at the end

        emailList.append(EmailMessage(msgId, sender, subject, date, category))

    return emailList



def getEmailIdList(category):
    
    # List messages (Gmail returns these in reverse chronological order by default)
    results = gmailService.users().messages().list(userId='me',
                                                   q=f"category:{category} label:inbox").execute()
    messages = results.get('messages', [])

    emailList = []          # the list to return
    for msg in messages:
        emailList.append(msg['id'])

    return emailList




#######################################
# MY SERVICES
#######################################

class EmailMessage:
    def __init__(self, id, sender, subject, date, category):
        self.id      = str(id)
        self.sender  = str(sender)
        self.subject = str(subject)
        self.date    = str(date)
        self.category= str(category)                

    def __str__(self):
        result  =                self.id
        result += " from: "    + self.sender
        result += " subject: " + self.subject
        result += " date0: "   + self.date
        result += " in: "      + self.category                
        return result



class EmailId:

    primaryIds = getEmailIdList("primary")
    
    def __init__(self, category):
        self.prevId   = None                       # the most recent id already processed previously
        self.fileName = "latest_"+category+".txt"  # where saved

    # First time processed() invoked, it will be with the most recent emailId
    # Save the previous one from fileName in self.prevId
    # Store that new given emailId in the file

    def processed(self, emailId):
        if self.prevId == None:
            # first time processed() called, whuch is the most recent id
            # remember it, and record it in file
            try:
                with open(self.fileName, "r") as file:
                    self.prevId = file.readline().split()[0]
            except:
                self.prevId     = ""        

            with open(self.fileName, "w") as file:
                file.write(emailId + " is the most recent email id already processed")
            
        return emailId == self.prevId

        



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

    idService  = {"promotions" : EmailId("promotions"),  # To check if email id previously processed
                  "social"     : EmailId("social"),
                  "primary"    : EmailId("primary"),                  
                  "updates"    : EmailId("updates")}
    
    ignore = []
    emails =  getEmailList('primary', ignore)
    """
    sendEmail("Social emails",
              socialEmails(emails, relevance))
    """

    
    for e in emails:
        print(e.subject)
