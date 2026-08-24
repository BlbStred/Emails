# Uses OpenAI to see which recent emails classified as
# promotion, social, or updates
# are actually relevant

import os
import sys
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my
import GmailService
import AIservice
import ParsedMessage

# Settings common to all my programs
my.init()


#######################################
# IDSERVICE: Detection of previously processed messages
#######################################

# This class remembers in a file which messages were processed previously
class EmailId:

    def __init__(self, category):
        self.prevId   = None                       # the most recent id already processed before
        self.fileName = "latest_"+category+".txt"  # where saved

    # First time processed() is invoked, it will be with the most recent emailId.
    # Save the previous one from fileName in self.prevId
    # Store that new given emailId in the file.

    
    def processed(self, emailId):
        if self.prevId == None:
            # First time processed() is called -- which makes emailId is the most recent id.
            # Store the id from the file in prevId for comparison with incoming ones, and
            # record the given emailId in the file
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


    
# Create the services for each category of interest,
# and save them in a dictionary

idService = {'promotions': EmailId('promotions'),   
             'social'    : EmailId('social'),
             'updates'   : EmailId('updates')}               




#######################################
# GMAIL message extraction
#######################################
        
gmailService = GmailService.GmailService()

# getEmailList() returns a list of messages of interest.
# It uses gmail query filter to decide which messages are of interest.
# In addition, below is my specific filter of message ids.

class Wanted:
    # idService allows us to check whether an email id has been processed in previous days
    def __init__(self, idService):
        self.idService = idService

    # This is the actual filter -- it detects previously processed messages
    def wanted(self, msgId):
        if self.idService.processed(msgId): return 'quit' # ignore this and subsequent messages
        return 'yes'                                      # do process this message
        

@my.timeit
def getEmailList(category):
    # List messages (Gmail returns these in reverse chronological order by default)
    # I rely on it in that if any message is seen previously, then all messages below also.
    # Collect messages satisfying:
    # - in the wanted category, e.g., Updates
    # - not also primary,
    # - still in inbox, as opposed to already moved to a user label
    
    messages = gmailService.rawMessages(f"category:{category} -category:primary label:inbox before:2026/08/20")

    # return the rawMessages after parsed into my data structure.
    # But filter out those messages not wanted by EmailId(category), i.e.,
    # messages processed in earlier days
    return ParsedMessage.parse(gmailService,
                               messages,
                               Wanted(idService[category]).wanted)





#######################################
# AI SERVICES
#######################################


aiService  = AIservice.AIservice()
    
#######################################
# SOCIAL EMAILS
#######################################

# Format the summary email and send it to myself
def socialEmails(emailList, relevance):

    relevant      = "<p>RELEVANT EMAILS:<br>"
    irrelevant    = "<p>IRRELEVANT EMAILS:<br>"
    unsure        = "<p>UNSURE ABOUT:<br>"
    failed        = "<p>FAILED:<br>"            
    numRelevant   = 0
    numIrrelevant = 0
    numUnsure     = 0
    numFailed     = 0        
    
    for e in emailList:

        # Prepare the reference link, that will be followed without overtaking the email
        ref = f"""<a href=https://mail.google.com/mail/u/0/#inbox/{e.id} target="_blank" rel="noopener noreferrer">
                {e.id} {e.category}&nbsp;from&nbsp;{e.sender}&nbsp;{e.date}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{e.subject}
                </a><br>
        """

        match relevance(e.subject, e.bodies):
            case 'YES':    relevant += ref; numRelevant   += 1
            case 'NO':   irrelevant += ref; numIrrelevant += 1
            case 'UNSURE': unsure   += ref; numUnsure     += 1
            case 'FAILED': failed   += ref; numFailed     += 1                            
            case _:        print("*** ERROR *** : Unknown relevance:", relevance(e.subject))

    # Avoid displaying empty lists
    if numRelevant   == 0: relevant   = ""
    if numIrrelevant == 0: irrelevant = ""
    if numUnsure     == 0: unsure     = ""
    if numFailed     == 0: failed     = ""            

    return (
        f"""
        <html>
          <body>
            Received {numRelevant} relevant, {numIrrelevant} irrelevant social emails,
            unsure about {numUnsure}, and failed on {numFailed}.
            {relevant}
            {unsure}
            {irrelevant}
            {failed}        
            </p>
         </body>
       </html>
       """
      )      




@my.timeit
def mymain():

    # list of messages from wanted categories
    parsedMessages =  (getEmailList('promotions') +
                       getEmailList('social')     +
                       getEmailList('updates'))

    # Collect all the parsedMessages into one email, and catagorize them using AI
    report = socialEmails(parsedMessages, aiService.emailRelevance)

    # Send the report to myself
    GmailService.sendEmail("Social emails", report)
                           
    



if __name__ == '__main__':
    
    mymain()
