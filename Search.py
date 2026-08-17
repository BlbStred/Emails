





import os.path
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import EmailMessage
import GmailService


# Reconfigure stdout to handle replace unprintable character with something like '?'
# instead of crashing
sys.stdout.reconfigure(errors='replace')

if __name__ == '__main__':
   
    gmailService = GmailService.GmailService()
    
    ignore = []
    emails =  EmailMessage.getEmailList(gmailService,
                                        gmailService.emailList('', 'yihsin'), ignore)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n\n", e, flush=True)
