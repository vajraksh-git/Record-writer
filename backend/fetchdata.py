from supabase import *
from dotenv import load_dotenv
import os
import requests

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(url)
print(key)


supabase: Client = create_client(url, key)
response = (
    supabase.table("jobs")
    .select("*")
    .execute()
)

#--------------------processing------------------
data = response.data
file_url = data[-1]["file_url"] # Use this!
print(f"Downloading from: {file_url}")

download_response = requests.get(file_url) # Use the 'file_url' variable
if download_response.status_code == 200:
    if file_url.endswith("pdf"):
        
        with open("Files_Downloaded/downloaded_file.pdf", "wb") as f:
            f.write(download_response.content) 
            print("Download saved! -- pdf")
         
    elif   file_url.endswith("jpeg"): 
        with open("Files_Downloaded/downloaded_file.jpeg", "wb") as f:
            f.write(download_response.content) # Use .content for binary
            print("Download saved! -- jpeg")
            
else:
    print("Failed to download")
    
    
