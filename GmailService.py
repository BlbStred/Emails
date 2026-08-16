import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GmailService:
    
    def __init__(self):
        
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
       
                
    def service(self):
        return self.serv

    

    def emailList(self, category):
        messages = []   # accumulates all the pages, which google provides page by page

        # The function list(..., pageToken=pageToken) below takes a pageToken as argument.
        # It provides the next page of emails to list.
        # If it is None then it indicates the first page.
        # list() sets it to the next page, which is None for the last page.
        pageToken = None # ...list(...,pageToken=pageToken) will set it to non-None when finished
        
        while True:
            # List messages (Gmail returns these in reverse chronological order by default)
            results = self.serv.users().messages().list(userId='me',
                                                        q=f"label:yihsin",  # query
                                                        maxResults=100,     # max results returned
                                                        pageToken=pageToken).execute()
            messages.extend(results.get('messages', []))
            
            # Check if another page exists
            pageToken = results.get('nextPageToken')
            if not pageToken:
                break
            
        return messages
    


