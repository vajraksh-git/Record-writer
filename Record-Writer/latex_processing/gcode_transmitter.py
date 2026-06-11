import serial
import time

def send_gcode_to_arduino(gcode_file_path, serial_port, baud_rate=115200):
    # Open the serial connection to the plotter
    with serial.Serial(serial_port, baud_rate, timeout=1) as ser:

        print(f"Connected to {serial_port} at {baud_rate} baud.")
        ser.reset_input_buffer()
        
        # Read the G-code file
        with open(gcode_file_path, 'r') as f:
            gcode_lines = f.readlines()
        
        # Send each line of G-code to the plotter
        for line in gcode_lines:
            line = line.strip()
            if not line or line.startswith(';'):  # Skip empty lines and comments
                continue
            
            print(f"Sending: {line}")
            ser.write((line + '\n').encode('utf-8'))  # Send the line followed by a newline
            
            while True:
                response = ser.readline().decode('utf-8').strip()
                if 'ok' in response:
                    break
                elif 'error' in response:
                    print(f"⚠️ GRBL reported an error on line: {line} -> {response}")
                    break
if __name__ == "__main__":
    gcode_file_path = "gcodes/"  # Path to your G-code file
    serial_port = "dev/tty/ACM0"  # Update with your serial port (e.g., COM3 on Windows or /dev/ttyUSB0 on Linux)
    
    send_gcode_to_arduino(gcode_file_path, serial_port)