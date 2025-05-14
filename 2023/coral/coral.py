import cv2
import numpy as np
import cadquery as cq

totalpicture = 8

bgr_values = []


def get_bgr(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        bgr = img[y, x]
        bgr_values.append(bgr)
        print("BGR value at ({}, {}): {}".format(x, y, bgr))

# 循環載入圖片
for i in range(1,totalpicture):
    stri = str(i)
    path = str(r"C:\Users\asus\Desktop\Leon\ROV\coral library\sample\CORAL (" + stri + ").jpg")
    img = cv2.imread(path)

    # 顯示圖片並等待滑鼠事件
    x = int((img.shape[0]) / 2)
    y = int((img.shape[1]) / 2)
    resize = cv2.resize(img, (y, x))
    cv2.imshow('image', resize)
    cv2.setMouseCallback('image', get_bgr)
    cv2.waitKey(0)

# 計算所有點擊位置的BGR數值的最大值和最小值
bgr_values = np.array(bgr_values)
b_min, g_min, r_min = np.min(bgr_values, axis=0)
b_max, g_max, r_max = np.max(bgr_values, axis=0)
print("Minimum BGR values: ({}, {}, {})".format(b_min, g_min, r_min))
print("Maximum BGR values: ({}, {}, {})".format(b_max, g_max, r_max))


lower_green = np.array([r_min, g_min, b_min])
upper_green = np.array([r_max, g_max, b_max])
standardrect = 2

totalheight = 0
totallength = 0
biggestlength = 0
smallestlength = 1000
biggestheight = 0
smallestheight = 1000



for i in range(1,totalpicture):
    stri = str(i)
    path = str(r"C:\Users\asus\Desktop\Leon\ROV\coral library\sample\CORAL (" + stri + ").jpg")
    originside = cv2.imread(path)
    hsv = cv2.cvtColor(originside, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_green, upper_green)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    n = len(contours)
    print("lencontour=", n)
    def showpic(pic):
        x = int((pic.shape[0]) / 2)
        y = int((pic.shape[1]) / 2)
        resized = cv2.resize(pic, (y, x))
        cv2.imshow("result", resized)
        cv2.waitKey()
        cv2.destroyAllWindows()


    firstcon = cv2.arcLength(contours[0], True)
    secondcon = 0
    thirdcon = 0
    scnumber = 0
    tcnumber = 0
    fcnumber = 0
    for i in range(n):
        if abs(cv2.contourArea(contours[i], True)) > firstcon:
            tcnumber = scnumber
            scnumber = fcnumber
            fcnumber = i
            thirdcon = secondcon
            secondcon = firstcon
            firstcon = abs(cv2.contourArea(contours[i], True))
        elif abs(cv2.arcLength(contours[i], True)) > secondcon:
            tcnumber = scnumber
            scnumber = i
            thirdcon = secondcon
            secondcon = abs(cv2.contourArea(contours[i], True))
        elif abs(cv2.arcLength(contours[i], True)) > thirdcon:
            tcnumber = i
            thirdcon = abs(cv2.contourArea(contours[i], True))

    # print(fcnumber,scnumber,tcnumber,firstcon,secondcon,thirdcon)

    if cv2.matchShapes(contours[fcnumber], contours[scnumber], 1, 0.0) < 0.001:
        scnumber = tcnumber

    cv2.drawContours(originside, contours[fcnumber], -1, (0, 0, 255), 2)
    cv2.drawContours(originside, contours[scnumber], -1, (0, 255, 0), 2)
    x, y, w, h = cv2.boundingRect(contours[fcnumber])
    cv2.rectangle(originside, (x, y), (x + w, y + h), (255, 0, 0), 2)

    x1 = 10000
    x2 = 0
    fclen = len(contours[fcnumber])
    for i in range(fclen):
        fcround = np.array(contours[fcnumber][i])
        fcround = fcround[0, 0]
        if fcround < x1:
            x1 = fcround
            fnx1 = i
    for i in range(fclen):
        fcround = np.array(contours[fcnumber][i])
        fcround = fcround[0, 0]
        if fcround > x2:
            x2 = fcround
            fnx2 = i
    fnx1 = np.array(contours[fcnumber][fnx1])
    fnx11 = fnx1[0, 0]
    fnx12 = fnx1[0, 1]
    fnx2 = np.array(contours[fcnumber][fnx2])
    fnx21 = fnx2[0, 0]
    fnx22 = fnx2[0, 1]
    # print(fnx1,fnx2 )
    cv2.line(originside, (fnx11, fnx12), (fnx21, fnx22), (255, 0, 0), 2)

    y1 = 10000
    y2 = 0
    fclen = len(contours[fcnumber])
    for i in range(fclen):
        fcround = np.array(contours[fcnumber][i])
        fcround = fcround[0, 1]
        if fcround < y1:
            y1 = fcround
            fny1 = i
    for i in range(fclen):
        fcround = np.array(contours[fcnumber][i])
        fcround = fcround[0, 1]
        if fcround > y2:
            y2 = fcround
            fny2 = i

    fny1 = np.array(contours[fcnumber][fny1])
    fny11 = fny1[0, 0]
    fny12 = fny1[0, 1]
    fny2 = np.array(contours[fcnumber][fny2])
    fny21 = fny2[0, 0]
    fny22 = fny2[0, 1]
    # print(fny1,fny2 )
    cv2.line(originside, (fny11, fny12), (fny21, fny22), (255, 0, 0), 2)

    x1 = fnx11  # 取四点坐标
    y1 = fnx12
    x2 = fnx21
    y2 = fnx12

    x3 = fny11
    y3 = fny12
    x4 = fny21
    y4 = fny22

    k1 = (y2 - y1) * 1.0 / (x2 - x1)  # 计算k1,由于点均为整数，需要进行浮点数转化
    b1 = y1 * 1.0 - x1 * k1 * 1.0  # 整型转浮点型是关键
    if (x4 - x3) == 0:  # L2直线斜率不存在操作
        k2 = None
        b2 = 0
    else:
        k2 = (y4 - y3) * 1.0 / (x4 - x3)  # 斜率存在操作
        b2 = y3 * 1.0 - x3 * k2 * 1.0
    if k2 == None:
        x = x3
    else:
        x = (b2 - b1) * 1.0 / (k1 - k2)
    y = k1 * x * 1.0 + b1 * 1.0

    # print("matchpoints=", x, y)
    cv2.circle(originside, (int(x), int(y)), 2, (0, 0, 255), 3)

    showpic(originside)
    # SideLengthOfStandardSquare = input("請輸入基準正方形的邊長:")
    SLOSS = int(standardrect)

    (na, nb), radius2 = cv2.minEnclosingCircle(contours[scnumber])
    pixeldividebycm = radius2 / ((SLOSS / 2) * 1.41421356237301)  # =2
    # print("pixeldividebycm", pixeldividebycm)
    xlength = abs(fnx1[0, 0] - fnx2[0, 0])
    length = xlength / pixeldividebycm
    yheight = abs(fny1[0, 1] - fny2[0, 1])
    tophalf = abs(fny1[0, 1] - y)
    contants = yheight / tophalf
    height = (yheight / pixeldividebycm) / contants
    totalheight = totalheight + height
    totallength = totallength + length
    if length < smallestlength:
        smallestlength = length
    if length > biggestlength:
        biggestlength = length
    if height  < smallestheight:
        smallestheight = height
    if height > biggestheight:
        biggestheight = height
    print("length=", length)
    print("height=", height)
print("totallength=",totallength)
print("totalheight=",totalheight)
exactlength = (totallength-biggestlength-smallestlength)/(totalpicture-3)
exactheight = (totalheight-biggestheight-smallestheight)/(totalpicture-3)

print("exactlength=",exactlength)
print("exactheight=",exactheight)

length = exactlength*10
width = length/2
height = exactheight*10
lengthstr = str(length)
heightstr = str(height)
text1 = cq.Workplane("XY").text("length of coral="+ lengthstr+" mm.",10, 1).translate((100,100,0))
text2 = cq.Workplane("XY").text("height of coral="+ heightstr+" mm.",10, 1).translate((100,85,0))

head = (
    cq.Workplane("XZ")
    .lineTo(width, 0)
    .ellipseArc(width, height, angle1=0, angle2=90)
    .close()
    .revolve(360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0)))
result = text1 + text2 + head

cq.exporters.export(result,'result.stl')

cv2.waitKey()
cv2.destroyAllWindows()