import sys
import GmailService
import ParsedMessage
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my


if __name__ == '__main__':
   
    my.init()
    
    gmailService = GmailService.GmailService()
    
    wanted = lambda x: 'yes'   # all raw messages are wanted
    emails =  ParsedMessage.parse(gmailService,
                                  gmailService.rawMessages("label:yihsin"),
                                  wanted)
       
    for e in emails:
        if "Watch" not in e.subject:
            print("\n", e, flush=True)
