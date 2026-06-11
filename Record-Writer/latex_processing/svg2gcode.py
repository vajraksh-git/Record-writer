from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.compiler import Compiler, interfaces
from svg_to_gcode import TOLERANCES
import xml.etree.ElementTree as ET
import os
import subprocess 

class CustomPlotterGcode(interfaces.Gcode):
    def __init__(self):
        super().__init__()
        self.decimal_places = 2 
        self.last_x = 0.0
        self.last_y = 0.0
        self.min_delta = 0.00020 
        
        # --- NEW: DYNAMIC SCALE FACTOR ---
        self.scale_factor = 1.0 
        
        # --- SERVO PEN CONFIGURATION ---
        self.pen_up_angle = 90     
        self.pen_down_angle = 30   
        self.pen_transition_delay = 0.3  
        self.max_x = 190.0  
        self.max_y = 270.0  

    def linear_move(self, x=None, y=None, z=None):
        """Filters out micro-movements and applies automatic scaling to fit the bed."""
        
        # 1. SCALE THE RAW COORDINATES BEFORE DOING ANYTHING ELSE
        scaled_x = (x * self.scale_factor) if x is not None else None
        scaled_y = (y * self.scale_factor) if y is not None else None

        target_x = round(scaled_x, self.decimal_places) if scaled_x is not None else self.last_x
        target_y = round(scaled_y, self.decimal_places) if scaled_y is not None else self.last_y

        # 2. THE SAFETY LOOP: Check if scaled coordinates violate bounds
        if target_x < 0 or target_x > self.max_x or target_y < 0 or target_y > self.max_y:
            raise ValueError(
                f"\n❌ HARDWARE CRASH PREVENTED!\n"
                f"The SVG tried to move to: (X: {target_x}, Y: {target_y})\n"
                f"Your plotter limits are set to: (Max X: {self.max_x}, Max Y: {self.max_y})\n"
            )
        
        dx = abs(target_x - self.last_x)
        dy = abs(target_y - self.last_y)
        
        if dx < self.min_delta and dy < self.min_delta:
            return ";dropped_micro_step"  
            
        self.last_x = target_x
        self.last_y = target_y
        
        return super().linear_move(target_x, target_y, z)
        
    def laser_on(self, power=1.0):
        return f"M3 S{self.pen_down_angle}\nG4 P{self.pen_transition_delay}"

    def laser_off(self):
        return f"M3 S{self.pen_up_angle}\nG4 P{self.pen_transition_delay}"
        
    def set_laser_power(self, power):
        if power > 0:
            return f"M3 S{self.pen_down_angle}\nG4 P{self.pen_transition_delay}"
        return f"M3 S{self.pen_up_angle}\nG4 P{self.pen_transition_delay}"


def pre_process_and_calculate_scale(input_svg_path, max_x, max_y):
    """Calculates the dynamic scale factor, strips the background, and patches missing/empty tags."""
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    
    tree = ET.parse(input_svg_path)
    root = tree.getroot()
    
    # --- 1. THE BACKGROUND ASSASSIN ---
    for parent in root.iter():
        for child in list(parent):
            if child.tag.endswith('rect') and child.get('width') in ['100%', '100.0%']:
                parent.remove(child)
                print("   [*] Removed background page border.")

    # --- THE NEW FIX: EMPTY PATH PATCHER ---
    # matplotlib sometimes creates empty <path> tags for spaces. vpype crashes on these.
    for elem in root.iter():
        if elem.tag.endswith('path'):
            d_attr = elem.get('d')
            # If the 'd' attribute is missing or empty, inject a dummy dot
            if d_attr is None or d_attr.strip() == '':
                elem.set('d', 'M 0 0')

    # --- 2. EXTRACT DIMENSIONS & PATCH HEIGHT/WIDTH ---
    svg_width, svg_height = max_x, max_y
    if 'viewBox' in root.attrib:
        parts = root.attrib['viewBox'].split()
        if len(parts) == 4:
            svg_width = float(parts[2])
            svg_height = float(parts[3])
            
    root.set('width', f"{svg_width}px")
    root.set('height', f"{svg_height}px")
    
    # --- 3. CALCULATE THE SHRINK FACTOR ---
    scale_x = max_x / svg_width
    scale_y = max_y / svg_height
    scale_factor = min(scale_x, scale_y)
    
    if scale_factor > 1.0:
        scale_factor = 1.0 
        
    print(f"   [*] Native SVG Size: {svg_width:.1f}x{svg_height:.1f} | Dynamic Scale applied: {scale_factor:.4f}")
    
    tree.write(input_svg_path, encoding='utf-8', xml_declaration=True)
    return scale_factor

def svg2gcode(input_svg_path, output_gcode_path, decimal_places=2, curve_tolerance=0.4 , max_x=190.0, max_y=270.0):
    
    print(f"\n[*] Pre-processing {input_svg_path}...")
    dynamic_scale = pre_process_and_calculate_scale(input_svg_path, max_x, max_y)

    # --- THE FIX: FLATTEN MATPLOTLIB MATH ---
    # vpype destroys the invisible boxes and converts <use> tags into raw, plotter-ready paths
    flat_svg_path = input_svg_path.replace(".svg", "_flat.svg")
    try:
        subprocess.run(["vpype", "read", input_svg_path, "write", flat_svg_path], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"[-] Failed to flatten math symbols: {e.stderr}")
        return

    TOLERANCES['approximation'] = curve_tolerance
    
    gcode_compiler = Compiler(CustomPlotterGcode, movement_speed=1000, cutting_speed=300, pass_depth=0)
    gcode_compiler.interface.decimal_places = decimal_places
    gcode_compiler.interface.max_x = max_x
    gcode_compiler.interface.max_y = max_y
    gcode_compiler.interface.scale_factor = dynamic_scale

    # Read the new FLATTENED file instead of the raw one
    curves = parse_file(flat_svg_path) 
    gcode_compiler.append_curves(curves)
    raw_gcode = gcode_compiler.compile()
    
    # Clean up empty lines and dropped steps
    cleaned_gcode = "\n".join([
        line for line in raw_gcode.split('\n') 
        if line.strip() and not line.startswith(';dropped_micro_step')
    ])
    
    with open(output_gcode_path, 'w') as f:
        f.write(cleaned_gcode)
    
    print(f"[+] Optimization Complete! Servo Plotter G-code saved to {output_gcode_path}")
    
    # Optional cleanup: Delete the temp flat file
    if os.path.exists(flat_svg_path):
        os.remove(flat_svg_path)

def svg2gcode_batch(input_folder, output_folder, decimal_places=2, curve_tolerance=0.4 , max_x=190.0, max_y=270.0):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.svg'):
            input_path = os.path.join(input_folder, filename)
            output_filename = os.path.splitext(filename)[0] + '.gcode'
            output_path = os.path.join(output_folder, output_filename)
            svg2gcode(input_path, output_path, decimal_places, curve_tolerance , max_x, max_y)

if __name__ == "__main__":
    svg2gcode_batch("../svgs/ambarish_svg", "../gcodes/ambarish", decimal_places=5, curve_tolerance=0.1 , max_x=190, max_y=270)