import os
import sys
import cv2
import numpy as np
import time
from threading import Thread, Event
from queue import Queue, Empty

# Set the path for zbar library
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

try:
    from pyzbar.pyzbar import decode
except ImportError as e:
    print(f"Error importing pyzbar: {e}")
    print("Please ensure zbar is installed:")
    print("  brew install zbar")
    print("Then install pyzbar:")
    print("  pip install pyzbar")
    sys.exit(1)

def expand_shortened_url(identifier):
    return f"https://your-actual-domain.com/{identifier}"

def extract_lsb(img, bit_plane=0):
    return np.bitwise_and(img, 1 << bit_plane).astype(np.uint8) * 255

def decode_qr_content(content):
    # Check if it's a 6-digit number
    if content.isdigit() and len(content) == 6:
        expanded_url = expand_shortened_url(content)
        return f"Expanded URL: {expanded_url}"

    # If it looks like a URL, return it directly
    if content.startswith('http'):
        return f"Direct URL: {content}"

    # If none of the above, return the content as is with a note
    return f"Unprocessed content (might need custom decoding): {content}"

def find_and_decode_qr(img):
    try:
        decoded_objects = decode(img)
        for obj in decoded_objects:
            raw_content = obj.data.decode('utf-8')
            return decode_qr_content(raw_content)
    except Exception as e:
        print(f"Error decoding QR code: {e}")
    return None

def process_frame(frame_queue, result_queue, stop_event):
    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=1)
            start_time = time.time()
            
            for bit_plane in range(4):  # Check first 4 bit planes
                lsb_frame = extract_lsb(frame, bit_plane)
                
                # Try each channel separately
                for channel in range(3):
                    qr_data = find_and_decode_qr(lsb_frame[:,:,channel])
                    if qr_data:
                        print(f"QR Code detected in bit plane {bit_plane}, channel {channel}")
                        print(f"Content: {qr_data}")
                        result_queue.put((qr_data, lsb_frame, bit_plane, channel))
                        return
                
                # Try all channels combined
                qr_data = find_and_decode_qr(lsb_frame)
                if qr_data:
                    print(f"QR Code detected in bit plane {bit_plane}, all channels")
                    print(f"Content: {qr_data}")
                    result_queue.put((qr_data, lsb_frame, bit_plane, -1))
                    return
            
            print("No hidden QR Code detected in this frame")
            
            elapsed = time.time() - start_time
            print(f"Frame processed in {elapsed:.2f} seconds")
            
            frame_queue.task_done()
        except Empty:
            continue
        except Exception as e:
            print(f"Error in process_frame: {e}")

def main():
    print("Initializing camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Camera initialized successfully.")
    print("LSB Hidden QR Code Detector is running. Press 'q' to quit.")

    cv2.namedWindow('LSB QR Scanner', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('LSB QR Scanner', 640, 480)

    frame_queue = Queue(maxsize=1)
    result_queue = Queue()
    stop_event = Event()

    worker = Thread(target=process_frame, args=(frame_queue, result_queue, stop_event))
    worker.start()

    last_qr_time = 0
    qr_cooldown = 2  # seconds
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            frame_count += 1
            current_time = time.time()
            
            if frame_count % 30 == 0:  # Print FPS every 30 frames
                fps = frame_count / (current_time - start_time)
                print(f"FPS: {fps:.2f}")
                frame_count = 0
                start_time = current_time

            cv2.putText(frame, "Scanning for hidden QR...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if frame_queue.empty():
                frame_queue.put(frame)

            if not result_queue.empty():
                qr_data, lsb_frame, bit_plane, channel = result_queue.get()
                if current_time - last_qr_time > qr_cooldown:
                    print(f"Hidden QR Code content: {qr_data}")
                    display_frame = cv2.cvtColor(lsb_frame, cv2.COLOR_BGR2GRAY) if channel != -1 else lsb_frame
                    display_frame = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2BGR)
                    cv2.putText(display_frame, f"Hidden QR: {qr_data}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Bit Plane: {bit_plane}, Channel: {channel if channel != -1 else 'All'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow('Detected Hidden QR Code', display_frame)
                    last_qr_time = current_time

            cv2.imshow('LSB QR Scanner', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quit key pressed.")
                break

    finally:
        stop_event.set()
        worker.join()
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released and windows closed.")

if __name__ == "__main__":
    main()