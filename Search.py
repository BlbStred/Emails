





import os.path
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import EmailMessage
import GmailService


# Reconfigure stdout to handle errors gracefully
sys.stdout.reconfigure(errors='replace')



#######################################
# GMAIL SERVICES
#######################################
        


s = GmailService.GmailService()
gmailService = s.service() # To access gmail







    
    
if __name__ == '__main__':

   
    ignore = []
    emails =  EmailMessage.getEmailList(gmailService, s.emailList('', 'yihsin'), ignore)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n\n", e, flush=True)
