import subprocess
import os
import sys

def batch_compile_svgs(input_folder, output_folder):
    """Feeds all SVGs to Sameer's Rust compiler using a local binary."""
    # Fixed the Windows vs Linux executable extension
    executable = "./svg2gcode.exe" if sys.platform == "win32" else "./svg2gcode"
    
    if not os.path.exists(executable):
        print(f"❌ Error: Missing compiler engine! Put '{executable}' in this folder.")
        return
        
    os.makedirs(output_folder, exist_ok=True)
    
    success_count = 0
    
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.svg'):
            input_svg = os.path.join(input_folder, filename)
            output_gcode = os.path.join(output_folder, filename.replace('.svg', '.gcode'))
            
            print(f"[*] Compiling -> {filename}")
            
            # The Rust binary command with your exact hardware limits
            command = [
                executable, 
                input_svg, 
                "--tolerance", "0.2",    
                "--out", output_gcode,
                "--on", "M3 S55\nG4 P0.2",        # Servo Down + Delay
                "--off", "M3 S80\nG4 P0.2",       # Servo Up + Delay
                "--dimensions", "90mm,110mm",    # Hard CNC boundaries
                "--dpi" , "96",                 # Standard SVG DPI
                "--feedrate", "300" ,              # Cutting speed
            
            ]
            
            try:
                # subprocess handles the \n in the M3 commands perfectly without shell=True
                subprocess.run(command, check=True, capture_output=True)
                success_count += 1
            except subprocess.CalledProcessError as e:
                print(f"   [-] Failed to compile {filename}: {e.stderr.decode().strip()}")
                
    print(f"\n[+] Batch complete! Successfully processed {success_count} pages.")

if __name__ == "__main__":
    batch_compile_svgs("../svgs/example", "../gcodes/example")