import os
from dotenv import load_dotenv # run 'pip install python-dotenv'
from openai import OpenAI


class AIservice:

    def __init__(self):
        
        # Load environment variables from .env
        load_dotenv()
        
        self.aiService  = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Return YES, NO, UNSURE depending on AI's classification of the given topic
    # topic is typically the subject of an email
    def relevance(self, topic):
        print("topic:", topic)
        return "UNSURE"
        try:
            # The Request
            response = self.aiService.chat.completions.create(
                model="gpt-4o",
                seed=42,         # for determinism
                temperature=0,   # otherwise makes wrong decision with no reason
                messages=[
                    {"role"    : "system",
                     "content" : """You are a classifier.
                     Answer 'YES' if the user's text is relevant,
                     answer 'NO' if it is not relevant,
                     answer 'UNSURE' if you are not sure.
                     Provide a brief reason.
                     
                     All social media posts are not relevant,
                     except direct posts by Stephen Edwards (not mere comments on somebody's post).
                     
                     If the text informs me of a new message, searches, job availability, noticing me, or invitation
                     then it is not relevant.               
                     Any news item or public anouncement is not relevant.
                     Any offer of savings or advice is not relevant.
                     Anything designed to draw a person's attention without saying what it is about, is not relevant.
                     
                     Any kind of bank statement is relevant.
                     Anything concerning security is relevant.  
                     """},
                    
                    {"role": "user",
                     "content": topic}
                ]
            )
        
            result = response.choices[0].message.content
            print(topic, " --> ", result)
            return result.split()[0]  # YES, NO, UNSURE is the first word

        except Exception as e:
            # This catches API errors, connection issues, or encoding bugs
            print(f"*** ERROR *** : {e}")
            return 'UNSURE'
