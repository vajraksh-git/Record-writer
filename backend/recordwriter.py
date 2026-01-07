import random
from HersheyFonts import HersheyFonts

# --- CONFIGURATION ---
OUTPUT_FILE = "./lab_record.gcode"
TEXT_TO_WRITE = "potte"
FONT_SIZE = 0.5  # Scale factor (0.5 is approx handwriting size)
JITTER_AMOUNT = 0.1  # 0.1mm variation (Humanizer factor)

def humanize(value):
    """Adds small random noise to coordinates to mimic hand tremors."""
    noise = random.uniform(-JITTER_AMOUNT, JITTER_AMOUNT)
    return round(value + noise, 3)

def generate_gcode(text):
    # Load the default Hershey font (Script style looks more handwritten)
    # Styles: 'rowmans', 'cursive', 'futural', 'scripts'
    fonts = HersheyFonts() 
    fonts.load_default_font('cursive') 
    
    gcode = []
    
    # Header: Safety and Setup
    gcode.append("G21 ; Set units to mm")
    gcode.append("G90 ; Absolute positioning")
    gcode.append("M5  ; Pen Up Safety")
    gcode.append("G28 ; Auto Home (Optional)")
    
    # Get the "lines" from the library
    # The library returns a list of line segments: [(x1, y1), (x2, y2)]
    # This means "Draw from P1 to P2"
    lines = fonts.lines_for_text(text)
    
    current_x, current_y = 0, 0
    
    for start_point, end_point in lines:
        # Extract coordinates and scale them
        x1, y1 = start_point
        x2, y2 = end_point
        
        # Invert Y because Hershey fonts often assume Y goes DOWN (screen coords),
        # but CNC machines assume Y goes UP. 
        x1 = x1 * FONT_SIZE
        y1 = -y1 * FONT_SIZE 
        x2 = x2 * FONT_SIZE
        y2 = -y2 * FONT_SIZE
        
        # LOGIC:
        # 1. Move to the Start of the stroke (Pen Up)
        # We only add jitter to the draw commands, not the rapid moves usually.
        gcode.append(f"M5") 
        gcode.append(f"G0 X{x1:.3f} Y{y1:.3f}")
        
        # 2. Draw to the End of the stroke (Pen Down)
        # Apply Humanization here
        target_x = humanize(x2)
        target_y = humanize(y2)
        
        gcode.append(f"M3")
        gcode.append(f"G1 X{target_x} Y{target_y} F1500")

    # Footer: Finish up
    gcode.append("M5 ; Pen Up")
    gcode.append("G0 X0 Y0 ; Go Home")
    
    return gcode

# --- EXECUTION ---
print(f"Generating G-Code for: '{TEXT_TO_WRITE}'")
commands = generate_gcode(TEXT_TO_WRITE)

# Write to file
with open(OUTPUT_FILE, 'w') as f:
    for cmd in commands:
        f.write(cmd + "\n")

print(f"Success! Saved to {OUTPUT_FILE}")