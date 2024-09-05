import os
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import cv2
import numpy as np
from pyzbar.pyzbar import decode
import time
import signal

class LSBSteg:
    def __init__(self, im):
        self.image = im
        self.height, self.width, self.nbchannels = im.shape
        self.size = self.width * self.height
        
        self.maskONE = 1
        self.maskZERO = 254
        
        self.curwidth = 0
        self.curheight = 0
        self.curchan = 0

    def next_slot(self):
        if self.curchan == self.nbchannels - 1:
            self.curchan = 0
            if self.curwidth == self.width - 1:
                self.curwidth = 0
                if self.curheight == self.height - 1:
                    self.curheight = 0
                    return False
                else:
                    self.curheight += 1
            else:
                self.curwidth += 1
        else:
            self.curchan += 1
        return True

    def read_bit(self):
        val = self.image[self.curheight, self.curwidth][self.curchan]
        val = int(val) & self.maskONE
        self.next_slot()
        if val > 0:
            return "1"
        else:
            return "0"

    def read_byte(self):
        return self.read_bits(8)

    def read_bits(self, nb):
        bits = ""
        for i in range(nb):
            bits += self.read_bit()
        return bits

    def decode_binary(self):
        l = int(self.read_bits(64), 2)
        output = b""
        for i in range(l):
            output += bytes([int(self.read_byte(), 2)])
        return output

def timeout_handler(signum, frame):
    raise TimeoutError("Function call timed out")

def extract_hidden_data(image, timeout=5):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        steg = LSBSteg(image)
        result = steg.decode_binary()
        signal.alarm(0)  # Cancel the alarm
        return result
    except TimeoutError:
        print("LSB extraction timed out")
        return None

def scan_lsb_qr_from_camera():
    print("Initializing camera...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    print("Camera initialized successfully.")
    
    last_scan_time = 0
    scan_interval = 1  # Minimum time (in seconds) between scans

    print("LSB QR Code Scanner is running. Press 'q' to quit.")

    frame_count = 0
    while True:
        print(f"Reading frame {frame_count}...")
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        frame_count += 1
        print(f"Processing frame {frame_count}...")

        # Display the original frame immediately
        cv2.imshow('Original Frame', frame)
        print("Displayed original frame.")

        try:
            # Extract hidden data using LSB with a timeout
            hidden_data = extract_hidden_data(frame, timeout=2)

            if hidden_data is not None:
                # Convert hidden data to image
                nparr = np.frombuffer(hidden_data, np.uint8)
                hidden_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if hidden_image is not None:
                    print("Hidden image extracted successfully.")
                    # Try to decode QR codes in the hidden image
                    decoded_objects = decode(hidden_image)

                    current_time = time.time()

                    for obj in decoded_objects:
                        # If enough time has passed since the last scan, print the data
                        if current_time - last_scan_time > scan_interval:
                            qr_data = obj.data.decode('utf-8')
                            print(f"LSB QR Code detected: {qr_data}")
                            last_scan_time = current_time

                    # Display the hidden image (optional)
                    cv2.imshow('Hidden Image', hidden_image)
                    print("Displayed hidden image.")
                else:
                    print("Failed to decode hidden image")
            else:
                print("No hidden data extracted")

        except Exception as e:
            print(f"Error processing frame: {str(e)}")

        # Check for 'q' key to quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quit key pressed. Exiting...")
            break
        elif key != 255:
            print(f"Key pressed: {key}")

    print("Releasing camera and closing windows...")
    cap.release()
    cv2.destroyAllWindows()
    print("Camera released and windows closed.")

if __name__ == "__main__":
    try:
        scan_lsb_qr_from_camera()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        print("Script execution completed.")