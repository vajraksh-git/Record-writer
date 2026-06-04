import os
import json
from PIL import Image
from google import genai
from google.genai import types

# 🔌 Import the dot-env connector
from dotenv import load_dotenv
load_dotenv() # This instantly searches for a .env file and loads its variables into system memory

def extract_handwritten_math():
    image_path = "image.png" 
    output_json_path = "math_results.json"
    
    if not os.path.exists(image_path):
        print(f"[-] Error: Please place your image at '{image_path}'")
        return

    # Now client() automatically grabs the key from your .env file!
    client = genai.Client()
    
    print("[*] Opening handwritten math asset...")
    img = Image.open(image_path)

    prompt = """
    Analyze this handwritten math document. Extract the content section by section, keeping the natural reading order.
    For standard text sentences, write them out clearly.
    For math equations, integrals, and formulas, convert them into clean LaTeX markdown format so the structure is perfectly preserved.
    
    Return the data as a JSON list of blocks, where each item has a "type" ("text" or "equation") and the "content".
    """

    print("[*] Sending image to Gemini 2.5 Flash...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',  # 🚀 Swapped to the active production model
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    print(f"[*] Saving structured math layout to {output_json_path}...")
    try:
        structured_data = json.loads(response.text)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)
        print("[+] Success! Your sequential text and math blocks are saved.")
        print(response.text)
    except Exception as e:
        print("[-] Failed to parse JSON, dumping raw response:")
        print(response.text)

if __name__ == "__main__":
    extract_handwritten_math()