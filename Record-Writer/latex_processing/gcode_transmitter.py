import serial
import time
import re
import math
import sys

def send_gcode_to_arduino(gcode_file_path, serial_port, baud_rate=115200, min_move=0.2):
    with serial.Serial(serial_port, baud_rate, timeout=1) as ser:

        print(f"[*] Connected to {serial_port}. Waiting for GRBL to boot...")
        
        # --- 1. BOOT HANDSHAKE ---
        start_time = time.time()
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"  [Booting]: {line}")
            if "Grbl" in line:
                break
            if time.time() - start_time > 5:
                print("  [!] Timeout waiting for GRBL. Forcing soft-reset...")
                ser.write(b'\x18') 
                start_time = time.time()

        time.sleep(0.5) 
        ser.reset_input_buffer()
        
        # --- 2. UNLOCK HANDSHAKE ---
        print("[*] Clearing Alarm Locks ($X)...")
        ser.write(b"$X\n")
        while True:
            res = ser.readline().decode('utf-8', errors='ignore').strip()
            if res:
                print(f"  [Unlock]: {res}")
            if 'ok' in res:
                break
            elif 'error' in res:
                break
        
        # --- 3. SERVO LIMIT HANDSHAKE ---
        print("[*] Setting hardware servo limits ($30=180)...")
        ser.write(b"$30=180\n")
        while True:
            res = ser.readline().decode('utf-8', errors='ignore').strip()
            if 'ok' in res:
                break

        print("\n[+] Plotter Online and Calibrated! Starting file stream...\n")
        
        with open(gcode_file_path, 'r') as f:
            gcode_lines = f.readlines()
            
        last_x, last_y = 0.0, 0.0
        x_pattern, y_pattern = re.compile(r'X([-0-9.]+)'), re.compile(r'Y([-0-9.]+)')
        dropped_count = 0
        
        print(f"[*] Streaming and filtering micro-movements < {min_move}mm...")
        
        for line in gcode_lines:
            original_line = line.strip()
            
            # Clean comments
            if ';' in original_line:
                original_line = original_line.split(';')[0].strip()
            if not original_line:  
                continue
            
            # --- PARSE MOVES ---
            # Check if this line contains coordinates (handles G0, G1, or raw modal coordinates)
            x_match, y_match = x_pattern.search(original_line), y_pattern.search(original_line)
            
            if x_match or y_match:
                target_x = float(x_match.group(1)) if x_match else last_x
                target_y = float(y_match.group(1)) if y_match else last_y
                
                # ONLY filter if it's a G1 cutting move. Never filter a G0 travel move!
                if "G0" not in original_line:
                    if math.hypot(target_x - last_x, target_y - last_y) < min_move:
                        dropped_count += 1
                        continue # Skip sending this micro-stutter line
                
                # Update our tracking coordinates
                last_x, last_y = target_x, target_y
                    
            # --- SEND & VERIFY ---
            ser.write((original_line + '\n').encode('utf-8'))  
            
            while True:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                if not response:
                    continue
                
                # --- THE CRASH DETECTOR ---
                if 'Grbl' in response or 'ALARM' in response:
                    print(f"\n[🚨 FATAL CRASH] The Arduino just rebooted mid-print!")
                    print(f"Hardware response: {response}")
                    print("--> Your power supply browned out the moment the motors/servo tried to move.")
                    print("--> UNPLUG THE 12V POWER BRICK, run on USB power only, and test again.\n")
                    sys.exit(1)
                    
                if 'ok' in response:
                    break
                elif 'error' in response:
                    print(f"⚠️ GRBL Error on: {original_line} -> {response}")
                    break

        print(f"\n[+] Print Complete!")
        print(f"[-] Successfully blocked {dropped_count} microscopic stutter lines.")

if __name__ == "__main__":
    gcode_file = "../gcodes/example/howu3.gcode" 
    port = "/dev/ttyUSB0"  # Perfect for Linux/Raspberry Pi
    send_gcode_to_arduino(gcode_file, port, min_move=0.02)