# requirements.txt standard constraint: Keep local repo clean
# Run: pip install svgpathtools
import random
import math
from svgpathtools import svg2paths

def inject_human_noise(x, y, total_distance):
    """
    Applies mathematical imperfection to fake human handwriting.
    """
    # 1. Baseline Wobble (Y-Axis drifts slowly across the page)
    wobble = 0.4 * math.sin(total_distance * 0.05)
    
    # 2. Micro-Jitter (Tiny random hand tremors on every point)
    jitter_x = random.gauss(0, 0.05)
    jitter_y = random.gauss(0, 0.05)
    
    return x + jitter_x, y + y_wobble + jitter_y

def convert_svg_to_noisy_gcode(svg_file, gcode_file):
    paths, _ = svg2paths(svg_file)
    
    with open(gcode_file, "w") as f:
        # Standard CNC Initialization Header
        f.write("G90 (Absolute positioning)\n")
        f.write("G21 (Units in millimeters)\n")
        f.write("M5  (Ensure pen is raised up)\n\n")
        
        total_distance = 0.0
        
        for path in paths:
            first_point = True
            
            # Divide each complex vector curve into tiny straight line segments
            for segment in path:
                # Extract raw coordinate points (Complex numbers: real=x, imag=y)
                start_x, start_y = segment.start.real, segment.start.imag
                end_x, end_y = segment.end.real, segment.end.imag
                
                # Apply scaling factor to map pixels/points directly to millimeters
                scale = 0.264  # Standard conversion from 96 DPI pixels to mm
                start_x, start_y = start_x * scale, start_y * scale
                end_x, end_y = end_x * scale, end_y * scale
                
                if first_point:
                    # Apply noise to the start of the line stroke
                    nx, ny = inject_human_noise(start_x, start_y, total_distance)
                    
                    f.write("M5 (Pen Up)\n")
                    f.write(f"G0 X{nx:.2f} Y{ny:.2f}\n")
                    f.write("M3 S1000 (Pen Down)\n")
                    first_point = False
                
                # Apply noise to the drawing path
                nx, ny = inject_human_noise(end_x, end_y, total_distance)
                f.write(f"G1 X{nx:.2f} Y{ny:.2f} F1500\n")
                
                # Track physical pen movement distance for the baseline drift wave
                total_distance += math.hypot(end_x - start_x, end_y - start_y)
                
        # End of file: Lift pen and go home
        f.write("\nM5 (Pen Up)\n")
        f.write("G0 X0 Y0 (Return to origin)\n")

# To run locally:
# convert_svg_to_noisy_gcode("output.svg", "output.gcode")