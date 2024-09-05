import cv2
import time

def main():
    print("Initializing camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Camera initialized successfully.")
    print("Camera feed should be visible. Press 'q' to quit.")

    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        frame_count += 1
        if frame_count % 30 == 0:  # Print every 30 frames
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time
            print(f"FPS: {fps:.2f}")

        cv2.imshow('Camera Feed', frame)
        print(f"Frame {frame_count} displayed.")  # Debug print

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quit key pressed.")
            break

    print("Releasing camera and closing windows...")
    cap.release()
    cv2.destroyAllWindows()
    print("Camera released and windows closed.")

if __name__ == "__main__":
    main()