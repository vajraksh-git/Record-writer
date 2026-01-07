import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter

def fix_orientation(input_file, output_file):
    writer = PdfWriter()
    reader = PdfReader(input_file)
    
    # Increase DPI to help Tesseract read small text better
    print("Converting PDF to images for analysis...")
    images = convert_from_path(input_file, dpi=300) 

    for i, image in enumerate(images):
        page = reader.pages[i]
        
        try:
            # Get OSD (Orientation and Script Detection)
            osd = pytesseract.image_to_osd(image)
            rotation = int(osd.split("Rotate: ")[1].split("\n")[0])
        except Exception as e:
            print(f"Page {i+1}: Could not detect text. Keeping original.")
            rotation = 0

        # LOGIC FIX: Rotate 'back' by the amount Tesseract detected
        if rotation != 0:
            print(f"Page {i+1}: Detected {rotation}° rotation. Correcting...")
            # pypdf.rotate() is Clockwise. 
            # If text is 90 (Right), we need -90 (Left) to fix it.
            page.rotate(-rotation) 
        else:
            print(f"Page {i+1}: Already upright.")

        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)
    print(f"Done! Saved to {output_file}")

fix_orientation("input.pdf", "Law_Fixed.pdf")