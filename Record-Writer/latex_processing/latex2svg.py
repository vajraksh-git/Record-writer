import svgutils.transform as sg
import matplotlib.pyplot as plt
import subprocess
import os
import xml.etree.ElementTree as ET
import shutil
import parse_latex
import textwrap # <--- ADD THIS
# ==============================================================================
# --- GLOBAL CNC & RECORD-WRITER CONFIGURATION ---
# ==============================================================================

# 1. Physical Paper Dimensions
CNC_BED_WIDTH_MM = 190.0   
CNC_BED_HEIGHT_MM = 270.0  

# 2. Margins 
MARGIN_X = 15.0
START_Y = 20.0
BOTTOM_MARGIN = 20.0
TEXT_WRAP_WIDTH_MM = CNC_BED_WIDTH_MM - (MARGIN_X * 2) 

# 3. Pen & Font Settings
TEXT_FONT_SIZE = "26"      
MATH_FONT_SIZE = 22        

# 4. Spacing Rules (Foam Padding Between Blocks)
PARAGRAPH_GAP = 2.0        
TEXT_TO_MATH_GAP = 2.0     
MATH_TO_TEXT_GAP = 2.0    
MATH_STACK_GAP = 4.0       

# --- SYSTEM CONSTANTS ---
MM2PX = 3.7795275591       
# ==============================================================================

def get_actual_svg_height_mm(svg_file_path):
    """Opens the generated SVG and reads its exact physical height."""
    if not os.path.exists(svg_file_path):
        return 0.0
        
    try:
        tree = ET.parse(svg_file_path)
        root = tree.getroot()
        height_str = root.attrib.get('height', '0').strip()
        
        # Strip the units and convert to millimeters
        if height_str.endswith('mm'):
            return float(height_str.replace('mm', ''))
        elif height_str.endswith('cm'): # THE FIX: Convert centimeters to millimeters
            return float(height_str.replace('cm', '')) * 10.0
        elif height_str.endswith('pt'): # Matplotlib uses Points (1pt = 0.352778mm)
            return float(height_str.replace('pt', '')) * 0.352778
        elif height_str.endswith('px'): # (1px = 0.264583mm)
            return float(height_str.replace('px', '')) * 0.264583
        else:
            return float(height_str)
    except Exception as e:
        print(f"[-] Failed to measure {svg_file_path}: {e}")
        return 10.0 # Fallback safety height

def text_to_single_stroke_svg(clean_text, output_svg_path):
    os.makedirs(os.path.dirname(output_svg_path) or '.', exist_ok=True)
    
    # --- NEW FIX: Hard-wrap the text using Python ---
    # We split by existing paragraphs, wrap them at 55 characters, and rejoin them.
    # You can change '55' if you want the text wider or narrower on the page!
    paragraphs = clean_text.split('\n')
    wrapped_paragraphs = [textwrap.fill(p, width=55) for p in paragraphs]
    wrapped_text = "\n".join(wrapped_paragraphs)
    
    command = [
        "vpype", "text", 
        "--font", "scriptc", 
        "--size", TEXT_FONT_SIZE,           
        # We removed the buggy --wrap flag because Python is doing the wrapping now      
        "--align", "left", 
        wrapped_text, "write", output_svg_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        with open("vpype_error.log", "a", encoding="utf-8") as log:
            log.write(f"FAILED TEXT:\n{clean_text}\nERROR:\n{e.stderr}\n{'-'*40}\n")
            
def render_math_to_svg(math_string, output_path):
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    try:
        plt.rc('mathtext', fontset='cm')
        fig = plt.figure(figsize=(0.01, 0.01))
        
        # Kill the hidden axes that draw boxes around the math
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')               
        fig.patch.set_visible(False) 
        
        fig.text(0, 0, f"${math_string}$", fontsize=MATH_FONT_SIZE, usetex=False, color='blue')
        
        # pad_inches=0 ensures no extra frame padding is calculated
        fig.savefig(output_path, format='svg', bbox_inches='tight', transparent=True, pad_inches=0.0)
        plt.close(fig)
    except Exception as e:
        with open("math_error.log", "a", encoding="utf-8") as log:
            log.write(f"FAILED MATH:\n{math_string}\nERROR:\n{str(e)}\n{'-'*40}\n")

def stitch_master_canvas(elements_list, output_path, width_mm, height_mm):
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    w_px = width_mm * MM2PX
    h_px = height_mm * MM2PX
    master_canvas = sg.SVGFigure(f"{w_px}", f"{h_px}")
    master_canvas.root.set("viewBox", f"0 0 {w_px} {h_px}")
    
    bg_string = f'<svg width="{w_px}" height="{h_px}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="white"/></svg>'
    paper_layer = sg.fromstring(bg_string)
    plots = [paper_layer.getroot()]
    
    for svg_file, x_pos_mm, y_pos_mm in elements_list:
        if not os.path.exists(svg_file): continue
        element = sg.fromfile(svg_file)
        plot = element.getroot()
        plot.moveto(x_pos_mm * MM2PX, y_pos_mm * MM2PX)
        plots.append(plot)
        
    master_canvas.append(plots)
    master_canvas.save(output_path)

def latex2svg(latex_file_path, output_directory="output_svgs"):
    print(f"[*] Starting Read-Back Precision Engine for: {latex_file_path}")
    
    pages_data = parse_latex.parse_latex_document(latex_file_path)
    if not pages_data:
        print("[-] Error: Parsing failed.")
        return

    os.makedirs("temp_svgs", exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)
    
    all_blocks = []
    for page in pages_data:
        all_blocks.extend(page)

    cnc_page_num = 1
    elements_list = []
    current_y = START_Y 
    previous_type = None

    print(f"\n[*] --- Assembling Master Canvas for CNC Page {cnc_page_num} ---")

    for block_index, block in enumerate(all_blocks):
        content = block['content']
        block_type = block['type']
        
        # 1. GENERATE INK FIRST
        temp_svg = f"temp_svgs/block_{block_index}_{block_type.lower()}.svg"
        
        if block_type == 'TEXT':
            text_to_single_stroke_svg(content, temp_svg)
            h = get_actual_svg_height_mm(temp_svg)
        elif block_type == 'MATH':
            render_math_to_svg(content, temp_svg)
            h = get_actual_svg_height_mm(temp_svg)
        elif block_type == 'SPACE':
            h = float(content) * 10
        else:
            h = 0

        # 2. CALCULATE THE FOAM PADDING GAP
        if previous_type is None:
            current_gap = 0
        elif block_type == 'MATH' and previous_type == 'MATH':
            current_gap = MATH_STACK_GAP
        elif block_type == 'TEXT' and previous_type == 'TEXT':
            current_gap = PARAGRAPH_GAP
        elif block_type == 'MATH' and previous_type == 'TEXT':
            current_gap = TEXT_TO_MATH_GAP  
        elif block_type == 'TEXT' and previous_type == 'MATH':
            current_gap = MATH_TO_TEXT_GAP  
        else:
            current_gap = PARAGRAPH_GAP
            
        # 3. PAGE BREAK TRIGGER
        if (current_y + current_gap + h) > (CNC_BED_HEIGHT_MM - BOTTOM_MARGIN):
            final_output_svg = f"{output_directory}/master_page_{cnc_page_num}.svg"
            stitch_master_canvas(elements_list, final_output_svg, CNC_BED_WIDTH_MM, CNC_BED_HEIGHT_MM)
            print(f"[+] Saved {final_output_svg} (Reached bottom of canvas)")
            
            cnc_page_num += 1
            print(f"\n[*] --- Assembling Master Canvas for CNC Page {cnc_page_num} ---")
            elements_list = []
            current_y = START_Y
            current_gap = 0 # Reset gap at the top of a new page

        # 4. ADVANCE CURSOR BY GAP
        current_y += current_gap

        # 5. APPEND TO STITCH LIST AT CURRENT_Y
        if block_type == 'TEXT':
            elements_list.append((temp_svg, MARGIN_X, current_y))
        elif block_type == 'MATH':
            elements_list.append((temp_svg, MARGIN_X + 15.0, current_y)) 
            
        # 6. ADVANCE CURSOR PAST THE INK
        current_y += h
        previous_type = block_type

    # Final Canvas Dump
    if elements_list:
        final_output_svg = f"{output_directory}/master_page_{cnc_page_num}.svg"
        stitch_master_canvas(elements_list, final_output_svg, CNC_BED_WIDTH_MM, CNC_BED_HEIGHT_MM)
        print(f"[+] Saved {final_output_svg}")
        
    print("\n[+] Rendering complete. SVGs are ready for G-Code plotting.")
    
    # --- SELF-CLEANING MECHANISM ---
    print("[*] Cleaning up temporary SVG fragments...")
    shutil.rmtree("temp_svgs", ignore_errors=True)
    print("[+] Cleanup finished.")

if __name__ == "__main__":
    latex2svg("../latex/ambarish.tex", output_directory="../svgs/ambarish_svg")