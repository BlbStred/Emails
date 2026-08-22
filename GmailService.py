# This file understands how to log into gmail
# and extract a list of messages.

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

import sys
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my

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

        # Try to create creds from token.json
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # If failed to create creds from token.json then
        # create them from credentials.json and write the result into token.json
        # for future use
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        # the result is a service object
        self.serv = build('gmail', 'v1', credentials=creds)
       
                
    def messagesObject(self):
        return self.serv.users().messages()

    
    def labelsObject(self):
        return self.serv.users().labels()

    
    # Returns a list of all raw messages matching the query.
    # The query is a string of entries saparated by blanks, of the form key:value
    # Keys are
    # from:
    # to:
    # subject:
    # cc:
    # bcc:    
    # category:   primary, promotions, social, updates, forums
    # label:      e.g. Receipts, Tax
    # in:         inbox, sent, draft, trash, spam, anywhere
    # is:         read, unread, starred, important, muted
    # after:      e.g., after:2026/12/24
    # before:     e.g., before:2026/12/24
    # newer_than: e.g., newer_than:7d   (7 days)
    # older_than: e.g., older_than:2m   (2 months)
    # has:attachment
    # filename:   e.g., filename:pdf OR filename:xyz.doc
    # size:       e.g., size:1000  (message, incl. attachments, at least 1000 bytes)
    # larger:     e.g., larger:1k  (message, incl. attachments, at least 1000 bytes)
    # smaller:    e.g., smaller:5m (message, incl. attachments, at at most 5MB)
    
    # Note on labels:
    # Gmail assigns to every message at least one system label
    # INBOX
    # SENT
    # DRAFT
    # SPAM
    # TRASH
    # UNREAD
    # STARRED
    # IMPORTANT
    # SNOOZE
    # CHAT
    # CATEGORY_PERSONAL
    # CATEGORY_UPDATES
    # CATEGORY_PROMOTIONS
    # CATEGORY_SOCIAL
    # CATEGORY_FORUMS
    # MUTED
    # SCHEDULED
    # In addition, a user can assign more user labels, e.g., tax
    # For readability, one can write
    # in:inbox instead of label:inbox, is:unread instead of label:unread
    # One must write category:personal instead of label:category_personal
    
    @my.timeit
    def rawMessages(self, query):
                
        messages = []   # collects all the pages, which google provides page by page

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
    


