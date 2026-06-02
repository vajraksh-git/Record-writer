import os
import json
from PIL import Image, ImageDraw

# Pure vision imports from Surya 0.4.0
from surya.ocr import run_ocr
from surya.model.detection import segformer
from surya.model.recognition.model import load_model
from surya.model.recognition.processor import load_processor

def extract_and_visualize():
    image_path = "image.png"
    output_image_path = "image_with_boxes.png"
    output_json_path = "results.json"
    
    if not os.path.exists(image_path):
        print(f"[-] Error: Please make sure '{image_path}' is inside this directory.")
        return
    
    print("[*] Loading image asset...")
    image = Image.open(image_path).convert("RGB")
    
    # Create a copy of the image that we can draw bounding boxes on top of
    visual_canvas = image.copy()
    draw = ImageDraw.Draw(visual_canvas)
    
    langs = ["en"]

    # Loading the raw vision weights straight into system RAM/CPU
    print("[*] Loading Segformer Line Detection Model...")
    det_processor, det_model = segformer.load_processor(), segformer.load_model()
    
    print("[*] Loading Text Recognition Model...")
    rec_model, rec_processor = load_model(), load_processor()

    # Execute the pure CPU vision math
    print("[*] Processing image natively on CPU...")
    predictions = run_ocr([image], [langs], det_model, det_processor, rec_model, rec_processor)
    page_data = predictions[0]

    extracted_records = []

    print("\n[*] Drawing bounding boxes and parsing data structures...")
    for idx, line in enumerate(page_data.text_lines):
        # 1. Grab coordinates: [x1, y1, x2, y2]
        bbox = line.bbox
        text_content = line.text
        
        # 2. Append data to our clean list for the JSON dump
        extracted_records.append({
            "block_index": idx + 1,
            "text": text_content,
            "bbox": bbox
        })
        
        # 3. Draw a bright red rectangle outline around the detected text block
        # width=3 gives it a solid, easily visible boundary line
        draw.rectangle(bbox, outline="red", width=3)

    # 💾 Save Option 1: Export structural coordinates to JSON
    print(f"[*] Saving structural telemetry to: {output_json_path}")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(extracted_records, f, indent=4, ensure_ascii=False)

    # 🎨 Save Option 2: Export the newly drawn visual asset
    print(f"[*] Saving visual bounding boxes canvas to: {output_image_path}")
    visual_canvas.save(output_image_path)

    print("\n========================================")
    print("✨ SUCCESS: Reclaimed output generated!")
    print("========================================")
    print(f"➔ View spatial boxes image: {output_image_path}")
    print(f"➔ View raw structured data: {output_json_path}")

if __name__ == "__main__":
    extract_and_visualize()