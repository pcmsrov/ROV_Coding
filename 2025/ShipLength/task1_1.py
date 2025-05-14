import cv2 
import numpy as np 

class PipeMeasurer:
    def __init__(self):
        self.points = []  # 儲存使用者選取的點座標
        self.original_image = None  # 儲存原始圖像
        self.reference_length = 0  # 已知參考長度（公分）
        self.reference_pixels = 0  # 參考長度對應的像素值

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:  # 當左鍵點擊時
            self.points.append((x, y))  # 記錄點擊位置
            cv2.circle(self.original_image, (x, y), 5, (0, 0, 255), -1)  # 在圖像上標記紅點（圓心在(x,y)，半徑5，紅色，實心）
            cv2.imshow('Original Image', self.original_image)  # 更新顯示圖像

            if len(self.points) == 4: # 當選取4個點後，自動計算未知長度
                self.calculate_unknown_length()

    def calculate_unknown_length(self): # 計算未知長度的函數
        if len(self.points) != 4:  # 確保有4個點
            return

        # 計算已知長度的像素距離（使用歐幾里得距離公式）
        pixel_length_known = np.sqrt((self.points[1][0] - self.points[0][0]) ** 2 +(self.points[1][1] - self.points[0][1]) ** 2)

        # 計算未知長度的像素距離
        pixel_length_unknown = np.sqrt((self.points[3][0] - self.points[2][0]) ** 2 +(self.points[3][1] - self.points[2][1]) ** 2)

        # 根據比例關係計算實際長度
        if self.reference_length > 0 and self.reference_pixels > 0:
            unknown_length = (pixel_length_unknown * self.reference_length) / pixel_length_known
            print(f"未知水管的實際長度: {unknown_length:.1f} cm")
        else:
            print("請先設置參考長度（按 'r' 鍵）")

    def process_image(self, image_path):  # 處理圖像的函數
        self.original_image = cv2.imread(image_path)  # 讀取圖像
        if self.original_image is None:  # 檢查是否成功讀取
            print(f"無法讀取圖片: {image_path}")
            return False

        self.original_image = cv2.resize(self.original_image,(self.original_image.shape[1] // 2,self.original_image.shape[0] // 2))  # 將圖像縮小一半（提高處理效率）

        cv2.imshow('Original Image', self.original_image)
        cv2.setMouseCallback('Original Image', self.mouse_callback)

        return True

    def set_reference(self, pixel_length, real_length):
        """設置參考長度"""
        self.reference_length = real_length  # 記錄實際長度（公分）
        self.reference_pixels = pixel_length  # 記錄像素長度
        print(f"已設置參考長度: {real_length:.1f} 公分 = {pixel_length:.1f} 像素")


def main():
    image_path = "Rov photo/t1.png"  # 替換為實際圖像路徑

    measurer = PipeMeasurer() # 創建PipeMeasurer實例

    # 處理指定圖像
    if measurer.process_image(image_path):
        print("請在圖片上點選四個點來測量水管長度")
        print("前兩個點為已知長度，後兩個點為未知長度")
        print("按 'r' 設置參考長度（用於校準測量）")
        print("按 'q' 退出")

        while True:
            key = cv2.waitKey(1) & 0xFF  # 等待鍵盤輸入
            if key == ord('q'):  # 按q退出
                break
            elif key == ord('r'):  # 按r設置參考長度
                if len(measurer.points) >= 2:  # 確保已選取至少2個點
                    # 獲取使用者輸入的實際長度
                    real_length = float(input("請輸入已知長度（公分）: "))
                    # 計算選取兩點之間的像素距離
                    pixel_length = np.sqrt((measurer.points[1][0] - measurer.points[0][0]) ** 2 +
                                           (measurer.points[1][1] - measurer.points[0][1]) ** 2)
                    measurer.set_reference(pixel_length, real_length)  # 設置參考長度
                else:
                    print("請先點選已知長度的兩個點")

        cv2.destroyAllWindows()  # 關閉所有OpenCV窗口
    else:
        print("圖片處理失敗")


if __name__ == "__main__":
    main() 
