
from google import genai
import os
from dotenv import load_dotenv 

class prompt():

    def __init__(self ,papersize, additional_prompt):
        self.prompt=additional_prompt
        self.papersize=papersize
        load_dotenv()

        local_filename="./Files_Downloaded/downloaded_file.pdf"
        
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        file_ref = client.files.upload(file=local_filename)

        self.response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[file_ref ,f"{self.prompt}"]
        )
    def getresult(self):
        return self.response
        

if __name__ == "__main__":
    genaii=prompt(papersize="A4" , additional_prompt="read and return text pls")
    result = genaii.getresult()
    print(result)