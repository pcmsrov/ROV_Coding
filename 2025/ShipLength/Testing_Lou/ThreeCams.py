import cv2
import numpy as np

# Initialize the video capture objects for cameras 1, 2, and 3
#cap1 = cv2.VideoCapture(1)  # Camera 1
#cap2 = cv2.VideoCapture(2)  # Camera 2
#cap3 = cv2.VideoCapture(3)  # Camera 3

cap1 = cv2.VideoCapture(1, cv2.CAP_MSMF)
cap2 = cv2.VideoCapture(2, cv2.CAP_MSMF)
cap3 = cv2.VideoCapture(3, cv2.CAP_MSMF)



while True:
    # Capture frame-by-frame from each camera
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    ret3, frame3 = cap3.read()

    # Check if frames are captured successfully
    if not ret1 or not ret2 or not ret3:
        print("Failed to grab frame from one or more cameras")
        break

    # Resize frames to the same height for concatenation
    height = min(frame1.shape[0], frame2.shape[0], frame3.shape[0])
    frame1 = cv2.resize(frame1, (int(frame1.shape[1] * height / frame1.shape[0]), height))
    frame2 = cv2.resize(frame2, (int(frame2.shape[1] * height / frame2.shape[0]), height))
    frame3 = cv2.resize(frame3, (int(frame3.shape[1] * height / frame3.shape[0]), height))

    # Concatenate frames horizontally
    combined_frame = np.hstack((frame1, frame2, frame3))

    # Display the resulting frame
    cv2.imshow('Cameras 1-3', combined_frame)

    # Press 'q' to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture objects and close all OpenCV windows
cap1.release()
cap2.release()
cap3.release()
cv2.destroyAllWindows()