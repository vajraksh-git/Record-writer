import os
import json
import cv2

def render_bounding_boxes():
    image_path = "image.png"
    json_path = "results.json"
    output_path = "opencv_output.png"

    # 1. Validation checks
    if not os.path.exists(json_path):
        print(f"[-] Error: Missing telemetry file '{json_path}'. Run your OCR script first!")
        return
    if not os.path.exists(image_path):
        print(f"[-] Error: Original source asset '{image_path}' not found.")
        return

    # 2. Read the structured JSON tracking data
    print(f"[*] Parsing data records from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    # 3. Load the source canvas with OpenCV
    print(f"[*] Processing image matrix via OpenCV...")
    img = cv2.imread(image_path)

    # 4. Iterative canvas drawing operations
    for record in ocr_data:
        idx = record["block_index"]
        text = record["text"]
        # Surya coordinates are floats: [x_min, y_min, x_max, y_max]
        bbox = record["bbox"]
        
        # OpenCV drawing vectors require integer pixel coordinates
        x1, y1, x2, y2 = [int(coord) for coord in bbox]

        # Draw the physical bounding box boundary
        # cv2.rectangle syntax: (image, top-left-pt, bottom-right-pt, color_BGR, thickness)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Draw a small text tag indicating the block index sequence number above the box
        label = f"#{idx}"
        # Adjust label placement so it doesn't clip past the upper borders
        text_y = max(y1 - 5, 15) 
        cv2.putText(img, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # 5. Output the finished graphic matrix
    print(f"[*] Exporting rendered spatial alignment map to: {output_path}")
    cv2.imwrite(output_path, img)
    
    print("\n[+] Render engine execution sequence complete. Open 'opencv_output.png' to check alignment.")

if __name__ == "__main__":
    render_bounding_boxes()