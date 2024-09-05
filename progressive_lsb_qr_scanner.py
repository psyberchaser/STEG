import os
import sys

# Set the path for zbar library
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import cv2
import numpy as np
import time
from queue import Queue
from threading import Thread, Timer

try:
    from pyzbar.pyzbar import decode
except ImportError as e:
    print(f"Error importing pyzbar: {e}")
    print("Please ensure zbar is installed:")
    print("  brew install zbar")
    print("Then install pyzbar:")
    print("  pip install pyzbar")
    sys.exit(1)

class TimeoutException(Exception):
    pass

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
        return ''.join(self.read_bit() for _ in range(nb))

    def decode_binary(self):
        start_time = time.time()
        l = int(self.read_bits(64), 2)
        output = bytearray()
        for i in range(l):
            output.extend(bytes([int(self.read_byte(), 2)]))
            if i % 100 == 0:  # Log progress every 100 bytes
                elapsed = time.time() - start_time
                print(f"Decoded {i}/{l} bytes in {elapsed:.2f} seconds")
        return bytes(output)

def extract_lsb_data(img, timeout=10):  # Increased timeout to 10 seconds
    result = [None]
    def extract():
        try:
            start_time = time.time()
            steg = LSBSteg(img)
            result[0] = steg.decode_binary()
            elapsed = time.time() - start_time
            print(f"LSB extraction completed in {elapsed:.2f} seconds")
        except Exception as e:
            print(f"Error in LSB extraction: {e}")

    timer = Timer(timeout, lambda: result.append(TimeoutException("LSB extraction timed out")))
    timer.start()
    extract_thread = Thread(target=extract)
    extract_thread.start()
    extract_thread.join(timeout)
    timer.cancel()

    if len(result) > 1:
        print(f"LSB extraction timed out after {timeout} seconds")
        return None
    return result[0]

def find_and_decode_qr(data):
    if data is None:
        return None
    start_time = time.time()
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None

    try:
        decoded_objects = decode(img)
        for obj in decoded_objects:
            elapsed = time.time() - start_time
            print(f"QR code decoded in {elapsed:.2f} seconds")
            return obj.data.decode('utf-8')
    except Exception as e:
        print(f"Error decoding QR code: {e}")
    
    return None

def process_frame(frame_queue, result_queue):
    while True:
        frame = frame_queue.get()
        if frame is None:
            break
        start_time = time.time()
        extracted_data = extract_lsb_data(frame)
        qr_data = find_and_decode_qr(extracted_data)
        elapsed = time.time() - start_time
        print(f"Frame processed in {elapsed:.2f} seconds")
        result_queue.put(qr_data)
        frame_queue.task_done()

def main():
    print("Initializing camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Camera initialized successfully.")
    print("Full LSB QR Code Scanner is running. Press 'q' to quit.")

    # Create a named window
    cv2.namedWindow('Full LSB QR Scanner', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Full LSB QR Scanner', 640, 480)

    frame_queue = Queue(maxsize=30)
    result_queue = Queue()

    # Start worker thread
    worker = Thread(target=process_frame, args=(frame_queue, result_queue))
    worker.start()

    frame_count = 0
    start_time = time.time()
    last_qr_time = 0
    qr_cooldown = 2  # seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        frame_count += 1
        current_time = time.time()
        
        if frame_count % 30 == 0:
            elapsed_time = current_time - start_time
            fps = frame_count / elapsed_time
            print(f"FPS: {fps:.2f}")

        # Add frame to queue for processing
        if not frame_queue.full():
            frame_queue.put(frame)

        # Check for QR code results
        if not result_queue.empty() and current_time - last_qr_time > qr_cooldown:
            qr_data = result_queue.get()
            if qr_data:
                print(f"QR Code content: {qr_data}")
                cv2.putText(frame, f"QR: {qr_data}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                last_qr_time = current_time

        # Display the frame
        cv2.imshow('Full LSB QR Scanner', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quit key pressed.")
            break

    # Clean up
    frame_queue.put(None)  # Signal the worker thread to exit
    worker.join()
    cap.release()
    cv2.destroyAllWindows()
    print("Camera released and windows closed.")

if __name__ == "__main__":
    main()