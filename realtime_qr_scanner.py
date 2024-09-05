import os
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import cv2
from pyzbar.pyzbar import decode
import time

def scan_qr_from_camera():
    # Initialize the camera
    cap = cv2.VideoCapture(0)  # 0 is usually the default camera

    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    last_scan_time = 0
    scan_interval = 1  # Minimum time (in seconds) between scans

    print("QR Code Scanner is running. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Try to decode QR codes in the frame
        decoded_objects = decode(frame)

        current_time = time.time()

        for obj in decoded_objects:
            # Draw a rectangle around the QR code
            points = obj.polygon
            if len(points) > 4:
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
            else:
                cv2.polylines(frame, [np.array(points, dtype=np.int32)], True, (0, 255, 0), 2)

            # If enough time has passed since the last scan, print the data
            if current_time - last_scan_time > scan_interval:
                qr_data = obj.data.decode('utf-8')
                print(f"QR Code detected: {qr_data}")
                last_scan_time = current_time

        # Display the frame
        cv2.imshow('QR Code Scanner', frame)

        # Check for 'q' key to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the camera and close windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        scan_qr_from_camera()
    except Exception as e:
        print(f"An error occurred: {str(e)}")