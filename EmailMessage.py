
class EmailMessage:
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


