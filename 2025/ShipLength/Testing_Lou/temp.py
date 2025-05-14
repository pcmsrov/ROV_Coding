# 打開攝像頭 1

#cap = cv2.VideoCapture(1)  #default method
#Windows method
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

#Linux method, not tested
#cap = cv2.VideoCapture(1, cv2.CAP_V4L2)