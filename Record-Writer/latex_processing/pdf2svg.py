import fitz
import os

def pdf2svg(inputfile_path, output_dir, target_max_mm=150.0):
    """
    Converts a PDF to SVG pages, mathematically capping the coordinate 
    bounding box to target_max_mm to prevent CNC scale blowouts.
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Extract just the filename to name the output files cleanly 
    # (e.g. gets "ambarish" from "../pdfs/ambarish.pdf")
    base_name = os.path.splitext(os.path.basename(inputfile_path))[0]
    
    # 3. Open the PDF
    doc = fitz.open(inputfile_path)

    for page in doc:
        page_width = page.rect.width
        page_height = page.rect.height
        
        # 4. CRITICAL FIX: No 2.83465 conversion! 
        # We scale the raw points directly to your target_max_mm ceiling.
        scale_factor = min(target_max_mm / page_width, target_max_mm / page_height)
        
        mat = fitz.Matrix(scale_factor, scale_factor)
        svg = page.get_svg_image(matrix=mat)
        
        # 5. Build the final save path and write the file
        output_path = os.path.join(output_dir, f"{base_name}_page_{page.number}.svg")
        with open(output_path, "w") as f:
            f.write(svg)

    print(f"Done! '{base_name}' scaled to max {target_max_mm} units and saved to '{output_dir}'.")

# To test this locally on your machine, call it like this:
if __name__ == "__main__":
    pdf2svg("../pdfs/ambarish.pdf", "../svgs/ambarish_svg", 150.0)