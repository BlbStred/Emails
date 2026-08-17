# Requires
# - environment variable settings in .env
# - credentials.json (which can generate token.json)


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
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv # run 'pip install python-dotenv'

class GmailService:
    
    def __init__(self):
        
        # Load environment variables from .env
        load_dotenv()

        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

        self.creds = None
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.serv = build('gmail', 'v1', credentials=self.creds)
       
                
    def messagesObject(self):
        return self.serv.users().messages()

    

    def messages(self, category, label):
        
        query = ""
        if category != "": query += f"category:{category} "
        if label    != "": query += f"label:{label} "
        
        messages = []   # accumulates all the pages, which google provides page by page

        # The function list(..., pageToken=pageToken) below takes a pageToken as argument.
        # It provides the next page of emails to list.
        # If it is None then it indicates the first page.
        # list() sets it to the next page, which is None for the last page.
        pageToken = None # ...list(...,pageToken=pageToken) will set it to non-None when finished
        
        while True:
            # List messages (Gmail returns these in reverse chronological order by default)
            results = self.messagesObject().list(userId='me',
                                                 q=query,
                                                 maxResults=100,     # max results returned
                                                 pageToken=pageToken).execute()
            messages.extend(results.get('messages', []))
            
            # Check if another page exists
            pageToken = results.get('nextPageToken')
            if not pageToken:
                break
            
        return messages
    


