import cv2
import mss
import numpy as np
import time
from datetime import datetime

# Function to capture a specific screen or monitor
def capture_screen_live(screen_number=1):
    with mss.mss() as sct:
        # Get all monitors
        monitors = sct.monitors

        # Check if the screen number exists
        if screen_number > len(monitors) - 1:
            raise ValueError(f"Screen {screen_number} does not exist. Available screens: {len(monitors) - 1}")

        # Select the target monitor
        monitor = monitors[screen_number]

        # Create a window for controls
        cv2.namedWindow('Controls')

        # Create trackbars for parameters
        cv2.createTrackbar('White Threshold', 'Controls', 128, 255, lambda x: None)
        cv2.createTrackbar('Min Length', 'Controls', 50, 500, lambda x: None)
        cv2.createTrackbar('Min Width', 'Controls', 10, 100, lambda x: None)

        # Infinite loop for live streaming
        while True:
            # Capture the screen
            screenshot = sct.grab(monitor)

            # Convert the screenshot to a NumPy array
            frame = np.array(screenshot)

            # Get current trackbar positions
            white_threshold = cv2.getTrackbarPos('White Threshold', 'Controls')
            min_length = cv2.getTrackbarPos('Min Length', 'Controls')
            min_width = cv2.getTrackbarPos('Min Width', 'Controls')

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)

            # Apply binary threshold
            _, binary = cv2.threshold(blurred, white_threshold, 255, cv2.THRESH_BINARY)

            # Morphological operations
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Draw pipes on the image
            frame_with_pipes = frame.copy()
            pipes_found = 0

            for contour in contours:
                # Calculate contour area
                area = cv2.contourArea(contour)

                # Get the minimum enclosing rectangle
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.int0(box)

                # Calculate the width and height of the rectangle
                width = rect[1][0]
                height = rect[1][1]

                # Calculate aspect ratio
                aspect_ratio = max(width, height) / (min(width, height) + 1e-6)

                # Check if it matches the characteristics of a pipe
                if (max(width, height) >= min_length and
                        min(width, height) >= min_width and
                        aspect_ratio >= 3.0):
                    # Draw the pipe contours
                    cv2.drawContours(frame_with_pipes, [box], 0, (0, 255, 0), 2)

                    # Calculate and display the length of the pipe
                    length = max(width, height)
                    x, y = box[0]
                    cv2.putText(frame_with_pipes,
                                f'Length: {int(length)}px',
                                (int(x), int(y) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 255, 0), 2)

                    pipes_found += 1

            # Display the binary image and the processed frame
            #cv2.imshow('Binary', binary)
            cv2.imshow('Pipe Detection', frame_with_pipes)

            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):  # Exit on 'q'
                break
            elif key == ord('c'):  # Capture image on 'c'
                if pipes_found > 0:
                    # Generate a filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"pipe_detected_{timestamp}.jpg"

                    # Save the image
                    cv2.imwrite(filename, frame_with_pipes)
                    print(f"Saved image: {filename}")
                    print(f"Detected {pipes_found} pipes")
                else:
                    print("No pipes detected. Adjust the parameters or object position.")

        # Close OpenCV windows
        cv2.destroyAllWindows()

# Main function
def main():
    try:
        # Specify the screen to capture (e.g., screen 2)
        screen_number = 2

        # Start capturing live video stream
        capture_screen_live(screen_number)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()