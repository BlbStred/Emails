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
        result += " from: "    + self.sender
        result += " subject: " + self.subject
        result += " date0: "   + self.date
        result += " in: "      + self.category
        result += " body: "    + self.body                        
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


def get_message_body(payload):
    """
    Extracts text/plain or text/html body from a full Gmail API message object.
    Returns a dict: {'plain': str, 'html': str}
    """
    
    bodies = {'plain': '', 'html': ''}

    def parse_parts(parts):
        
        for part in parts:
            mime_type = part.get('mimeType')
            body_data = part.get('body', {}).get('data')

            if body_data:
                # Gmail API uses URL-safe base64 encoding (- and _ instead of + and /)
                decoded_bytes = base64.urlsafe_b64decode(body_data)
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')

                if mime_type == 'text/plain' and not bodies['plain']:
                    bodies['plain'] = decoded_text
                elif mime_type == 'text/html' and not bodies['html']:
                    bodies['html'] = decoded_text

            # Recursively handle nested multi-part structures
            if 'parts' in part:
                parse_parts(part['parts'])

    # 1. Simple Single-Part Message
    
    if 'data' in payload.get('body', {}):
        body_data = payload['body']['data']
        decoded_bytes = base64.urlsafe_b64decode(body_data)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        
        mime_type = payload.get('mimeType', 'text/plain')
        if mime_type == 'text/html':
            bodies['html'] = decoded_text
        else:
            bodies['plain'] = decoded_text

    # 2. Multi-Part Message (e.g., multipart/alternative, multipart/mixed)
    elif 'parts' in payload:
        parse_parts(payload['parts'])

    return bodies


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

        body = get_message_body(payload)['plain'] # Plaintext repn of body
        
        # headers is a list of dictionaries {'name: ..., 'value': ...}
        # To get the subject, for example, find the first dictionary {'name: 'Subject', 'value': ...}
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'),    'Unknown Sender')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'),    'Unknown Date')
        date    = re.split(r'[+-]', date)[0]     # Get rid of the universal time at the end

        parsedMessages.append(ParsedMessage(msgId, sender, subject, date,
                                            get_message_category(realMessage), body))

    return parsedMessages
