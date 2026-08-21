
import sys
from pathlib import Path

commonDir = "C:\\Users\\Dan\\Documents\\Computing\\common"
if commonDir not in sys.path:
    sys.path.insert(0, str(Path(commonDir).resolve()))

import my

if __name__ == "__main__":
    numFailed = 0
    
    numFailed += my.regression("Search")
    numFailed += my.regression("SocialEmailsAgent")    

    print("%2d tests failed" % numFailed)

    
