import os
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import cv2
import numpy as np
from pyzbar.pyzbar import decode

class LSBSteg:
    def __init__(self, im):
        self.image = im
        self.height, self.width, self.nbchannels = im.shape
        self.size = self.width * self.height
        
        self.maskONE = 1  # 00000001
        self.maskZERO = 254  # 11111110
        
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
                    return False  # No more slots available
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

def extract_hidden_data(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image at {image_path}")
    steg = LSBSteg(img)
    return steg.decode_binary()

def save_extracted_image(data, output_path):
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    cv2.imwrite(output_path, img)

def decode_qr(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image at {image_path}")
    decoded_objects = decode(img)
    for obj in decoded_objects:
        return obj.data.decode('utf-8')
    return None

def main():
    input_image = 'hidden_qr.png'
    extracted_image_path = 'extracted_qr.png'

    if not os.path.exists(input_image):
        print(f"Error: The file {input_image} does not exist in the current directory.")
        return

    try:
        # Extract hidden data
        hidden_data = extract_hidden_data(input_image)

        # Save extracted data as an image
        save_extracted_image(hidden_data, extracted_image_path)

        print(f"Extracted image saved as {extracted_image_path}")

        # Decode QR code
        qr_data = decode_qr(extracted_image_path)

        if qr_data:
            print(f"QR Code content: {qr_data}")
        else:
            print("No QR code found in the extracted image.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()