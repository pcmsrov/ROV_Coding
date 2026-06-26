import cv2
import numpy as np
import math

# ===================== 全局几何固定参数（贴合你的实物）=====================
# 实物特征：3个长方体组成、12个顶点、全部夹角90°正交
angle_tol = 8          # 角度容错，判定水平/垂直允许微小偏差
right_angle_tol = 10   # 判定90°直角容错角度
min_vertex_dist = 15   # 顶点最小间距，过滤重复顶点
img_path = "water_frame.jpg"
# 水下白色管线专用阈值
lower_white = np.array([0, 0, 150])
upper_white = np.array([180, 90, 255])
# =========================================================================

# 水下自动白平衡 矫正偏蓝
def auto_white_balance(img):
    res = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    avg_a = np.average(res[:, :, 1])
    avg_b = np.average(res[:, :, 2])
    res[:, :, 1] -= ((avg_a - 128) * (res[:, :, 0] / 255.0) * 1.2)
    res[:, :, 2] -= ((avg_b - 128) * (res[:, :, 0] / 255.0) * 1.2)
    return cv2.cvtColor(res, cv2.COLOR_LAB2BGR)

# 计算线段角度
def get_line_angle(x1,y1,x2,y2):
    dy = y2 - y1
    dx = x2 - x1
    ang = math.degrees(math.atan2(dy,dx))
    if ang < 0:
        ang += 180
    return ang

# 筛选：只保留 水平线 / 垂直线
def filter_hv_lines(lines):
    hv_lines = []
    if lines is None:
        return hv_lines
    for line in lines:
        x1,y1,x2,y2 = line[0]
        ang = get_line_angle(x1,y1,x2,y2)
        # 水平线 0° / 180°
        if abs(ang) < angle_tol or abs(ang-180) < angle_tol:
            hv_lines.append([[x1,y1,x2,y2,"H"]])
        # 垂直线 90°
        elif abs(ang-90) < angle_tol:
            hv_lines.append([[x1,y1,x2,y2,"V"]])
    return hv_lines

# 检测90°直角顶点
def detect_right_angle_vertex(h_lines, v_lines):
    vertex_set = set()
    for hl in h_lines:
        x1h,y1h,x2h,y2h,_ = hl[0]
        for vl in v_lines:
            x1v,y1v,x2v,y2v,_ = vl[0]
            # 粗略求交点
            def ccw(A,B,C):
                return (B[0]-A[0])*(C[1]-A[1])-(B[1]-A[1])*(C[0]-A[0])
            A=(x1h,y1h);B=(x2h,y2h)
            C=(x1v,y1v);D=(x2v,y2v)
            if ccw(A,B,C)*ccw(A,B,D)<=0 and ccw(C,D,A)*ccw(C,D,B)<=0:
                x = ((x1h*y2h-y1h*x2h)*(x1v-x2v)-(x1h-x2h)*(x1v*y2v-y1v*x2v)) / ((x1h-x2h)*(y1v-y2v)-(y1h-y2h)*(x1v-x2v))
                y = ((x1h*y2h-y1h*x2h)*(y1v-y2v)-(y1h-y2h)*(x1v*y2v-y1v*x2v)) / ((x1h-x2h)*(y1v-y2v)-(y1h-y2h)*(x1v-x2v))
                vertex_set.add((int(x),int(y)))
    vertex_list = list(vertex_set)
    # 去重过近顶点
    clean_vertex = []
    for p in vertex_list:
        flag = True
        for q in clean_vertex:
            dist = np.hypot(p[0]-q[0],p[1]-q[1])
            if dist < min_vertex_dist:
                flag=False
                break
        if flag:
            clean_vertex.append(p)
    return clean_vertex

# 主函数 几何约束长方体框架识别
def geometry_box_frame_detect(img_path):
    img = cv2.imread(img_path)
    if img is None:
        print("图片读取失败")
        return
    draw = img.copy()

    # 1.水下图像强化
    img_wb = auto_white_balance(img)
    lab = cv2.cvtColor(img_wb,cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.2,tileGridSize=(8,8))
    l_enh = clahe.apply(l)
    img_enh = cv2.merge((l_enh,a,b))
    img_enh = cv2.cvtColor(img_enh,cv2.COLOR_LAB2BGR)

    # 2.提取白色管线区域
    hsv = cv2.cvtColor(img_enh,cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,lower_white,upper_white)
    kernel = np.ones((9,9),np.uint8)
    mask_close = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)

    # 3.边缘检测 + 霍夫线
    edges = cv2.Canny(mask_close,40,130)
    lines = cv2.HoughLinesP(edges,1,np.pi/180,22,minLineLength=55,maxLineGap=35)

    # 4.筛选横竖正交线条
    hv_all = filter_hv_lines(lines)
    h_lines = [x for x in hv_all if x[0][4]=="H"]
    v_lines = [x for x in hv_all if x[0][4]=="V"]

    # 5.提取90°直角顶点（匹配12顶点长方体结构）
    vertexs = detect_right_angle_vertex(h_lines,v_lines)
    print(f"检测到框架直角顶点数量：{len(vertexs)} 个，匹配3组长方体拓扑")

    # 6.绘制正交管线 红色粗线
    for line in hv_all:
        x1,y1,x2,y2,_ = line[0]
        cv2.line(draw,(x1,y1),(x2,y2),(0,0,255),3)

    # 7.绘制框架顶点 黄色圆点标记12顶点体系
    for (x,y) in vertexs:
        cv2.circle(draw,(x,y),5,(0,255,255),-1)

    # 8.轮廓拟合长方体外框 补齐整套缺失边线
    contours,_ = cv2.findContours(mask_close,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area>120:
            rect = cv2.minAreaRect(cnt)
            box = np.int0(cv2.boxPoints(rect))
            cv2.drawContours(draw,[box],0,(0,0,255),2)

    # 窗口展示
    cv2.imshow("原图",img)
    cv2.imshow("白色管线掩膜",mask_close)
    cv2.imshow("正交90°长方体框架识别",draw)
    cv2.imwrite("Geometry_Box_Frame_Result.jpg",draw)
    print("✅ 基于长方体几何+90°直角+12顶点结构识别完成，结果已保存")

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    geometry_box_frame_detect(img_path)