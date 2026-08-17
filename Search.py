import sys
import EmailMessage
import GmailService
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my


if __name__ == '__main__':
   
    my.init()
    
    gmailService = GmailService.GmailService()
    
    ignore = []
    emails =  EmailMessage.getEmailList(gmailService,
                                        gmailService.messages('', 'yihsin'), ignore)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n\n", e, flush=True)
