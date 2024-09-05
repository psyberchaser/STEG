import os
import sys

# Set the path for zbar library
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
import webbrowser

try:
    from pyzbar.pyzbar import decode
except ImportError as e:
    print(f"Error importing pyzbar: {e}")
    print("Please ensure zbar is installed:")
    print("  brew install zbar")
    print("Then install pyzbar:")
    print("  pip install pyzbar")
    sys.exit(1)

class LSBSteg:
    def __init__(self, img):
        self.img = img
        self.height, self.width, self.nbchannels = img.shape
        self.size = self.width * self.height
        
        self.maskONEValues = [1,2,4,8,16,32,64,128]
        self.maskONE = self.maskONEValues.pop(0)
        
        self.maskZEROValues = [254,253,251,247,239,223,191,127]
        self.maskZERO = self.maskZEROValues.pop(0)
        
        self.curwidth = 0
        self.curheight = 0
        self.curchan = 0

    def next_slot(self):
        if self.curchan == self.nbchannels-1:
            self.curchan = 0
            if self.curwidth == self.width-1:
                self.curwidth = 0
                if self.curheight == self.height-1:
                    self.curheight = 0
                    if self.maskONE == 128:
                        return None
                    else:
                        self.maskONE = self.maskONEValues.pop(0)
                        self.maskZERO = self.maskZEROValues.pop(0)
                else:
                    self.curheight += 1
            else:
                self.curwidth += 1
        else:
            self.curchan += 1
        return True

    def read_bit(self):
        val = self.img[self.curheight,self.curwidth][self.curchan]
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

def extract_lsb_data(img):
    steg = LSBSteg(img)
    return steg.decode_binary()

def find_and_decode_qr(data):
    if data is None:
        return None
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None

    try:
        decoded_objects = decode(img)
        for obj in decoded_objects:
            return obj.data.decode('utf-8')
    except Exception as e:
        print(f"Error decoding QR code: {e}")
    
    return None

def process_image(file_path):
    # Read the image
    img = cv2.imread(file_path)
    if img is None:
        print("Error: Unable to read the image.")
        return None

    # Extract LSB data
    extracted_data = extract_lsb_data(img)
    if extracted_data is None:
        print("Error: Failed to extract LSB data.")
        return None

    # Decode QR code
    qr_data = find_and_decode_qr(extracted_data)
    if qr_data is None:
        print("Error: No QR code found in the extracted data.")
        return None

    return qr_data

def open_file_dialog():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
    return file_path

def main():
    print("Please select an image file containing the hidden QR code.")
    file_path = open_file_dialog()
    
    if not file_path:
        print("No file selected. Exiting.")
        return

    print(f"Processing image: {file_path}")
    qr_content = process_image(file_path)

    if qr_content:
        print(f"QR Code content: {qr_content}")
        if qr_content.startswith(('http://', 'https://')):
            print("Opening URL in default browser...")
            webbrowser.open(qr_content)
        else:
            print("The QR code does not contain a valid URL.")
    else:
        print("Failed to extract or decode QR code from the image.")

if __name__ == "__main__":
    main()