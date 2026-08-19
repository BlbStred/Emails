# This file understands how information is stored in Gmail raw messages.
# It parses them and puts information of interest into ParsedMessage


import re
import base64

class ParsedMessage:
    def __init__(self, id, sender, subject, date, category, body):
        self.id      = str(id)
        self.sender  = str(sender)
        self.subject = str(subject)
        self.date    = str(date)
        self.category= str(category)
        self.body    = str(body)                        

    def __str__(self):
        result  =                self.id
        result += "\nfrom:    " + self.sender
        result += "\nsubject: " + self.subject
        result += "\ndate:    " + self.date
        result += "\nin:      " + self.category
        result += "\nbody:    " + self.body                        
        return result

    
def get_message_category(message_obj: dict) -> str:
    """
    Extracts the category name from a Gmail API message resource.
    
    :param message_obj: Dictionary representing the Gmail Message resource.
    :return: Friendly category name (e.g., 'Updates', 'Promotions', 'Personal').
    """
    labels = message_obj.get("labelIds", [])
    
    for label in labels:
        if label.startswith("CATEGORY_"):
            # Converts 'CATEGORY_PROMOTIONS' -> 'Promotions'
            return label.removeprefix("CATEGORY_").title()
            
    # Messages without an explicit CATEGORY_* label default to Main/Personal
    return "Personal"


def parsePartOrPayload(x):
    body_data = x.get('body', {}).get('data')
    if body_data:
        if x.get('mimeType', 'text/plain') == 'text/plain':
            # Gmail API uses URL-safe base64 encoding (- and _ instead of + and /)
            decoded_bytes = base64.urlsafe_b64decode(body_data)
            return decoded_bytes.decode('utf-8', errors='ignore')
        
    return None
    
# If any part contains plain text return that,
# otherwise return None
def parse_parts(parts):
    # parts is a list.
    # If any part in the list contains a body records the plain text portion
    # If a part has a list of parts itself, recurse
    for part in parts:
        result = parsePartOrPayload(part)
        if result: return result
            
        """
        # attachment
        if part.get('filename') and part.get('body', {}).get('attachmentId'):
        filename = part['filename']
        print("attached", filename)
        """

        # Recursively handle nested multi-part structures
        if 'parts' in part:
            result = parse_parts(part['parts'])
            if result: return result

                
def get_message_body(payload):
    """
    Extracts text/plain or text/html body from a full Gmail API message object.
    Returns a dict: {'plain': str, 'html': str}
    """

    # 1. Simple Single-Part Message
    
    if 'data' in payload.get('body', {}):
        return parsePartOrPayload(payload)

    # 2. Multi-Part Message (e.g., multipart/alternative, multipart/mixed)
    elif 'parts' in payload:
        return parse_parts(payload['parts'])

    return None


def parse(gmailService, rawMessages, ignoreIdList):
        
    parsedMessages = []          # the list to return
    for rawMessage in rawMessages:
        # Each rawMessage has just a dict with keys id and threadId
        # realMessage can be obtained from those
        
        msgId = rawMessage['id']
        realMessage = gmailService.messagesObject().get(userId='me', id=msgId).execute()
        
        # Extract headers 
        payload = realMessage.get('payload', {})  
        headers = payload.get('headers', [])

        body = get_message_body(payload) # Plaintext repn of body
        
        # headers is a list of dictionaries {'name: ..., 'value': ...}
        # To get the subject, for example, find the first dictionary {'name: 'Subject', 'value': ...}
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'),    'Unknown Sender')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'),    'Unknown Date')
        date    = re.split(r'[+-]', date)[0]     # Get rid of the universal time at the end

        parsedMessages.append(ParsedMessage(msgId, sender, subject, date,
                                            get_message_category(realMessage), body))

    return parsedMessages
