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
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my
import GmailService
import ParsedMessage
   
my.init()

    
# Load environment variables from .env
load_dotenv()




#######################################
# GMAIL SERVICES
#######################################
        


gmailService = GmailService.GmailService()

# Filter of message ids
class Wanted:
    def __init__(self, idService):
        self.idService = idService

    def wanted(self, msgId):
        if self.idService.processed(msgId): return 'quit' # ignore this and subsequent messages
        return 'yes'                                      # process this message
        

@my.timeit
def getEmailList(category, idService):
    # List messages (Gmail returns these in reverse chronological order by default)
    # I rely on that in that if any message seen previously, then all messages below also
    # Collect messages in the wanted category, but still in inbox --
    # nobody looked at it and moved it to a user label
    messages = gmailService.rawMessages(f"category:{category} -category:primary label:inbox before:2026/08/20")
        
    return ParsedMessage.parse(gmailService,
                               messages,
                               Wanted(idService).wanted)





#######################################
# MY SERVICES
#######################################




class EmailId:

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
            """
            with open(self.fileName, "w") as file:
                file.write(emailId + " is the most recent email id already processed")
            """
        return emailId == self.prevId

        



#######################################
# AI SERVICES
#######################################


aiService  = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Return YES, NO, UNSURE depending on AI's classification of the given topic
# topic is typically the subject of an email
def relevance(topic):
    print("topic:", topic)
    return  'UNSURE'
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
    print()
    print("Subject:", subject)
    print("Body:", body)
    return

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


@my.timeit
def mymain():
    
    emails =  (getEmailList('promotions', EmailId("promotions")) +
               getEmailList('social',     EmailId("social"))     +
               getEmailList('updates',    EmailId("updates")))
    
    sendEmail("Social emails",
              socialEmails(emails, relevance))
    



if __name__ == '__main__':
    
    mymain()
