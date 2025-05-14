import cv2
import numpy as np
import time


class CameraManager:
    def __init__(self):
        self.caps = []
        self.init_cameras()

    def init_cameras(self):
        """初始化所有摄像头"""
        self.release_all()
        self.caps = []

        # 尝试初始化3个摄像头
        for i in range(4):
            max_retries = 4
            for attempt in range(max_retries):
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    self.caps.append(cap)
                    print(f"成功初始化摄像头 {i}")
                    break
                else:
                    print(f"尝试 {attempt + 1}/{max_retries}: 摄像头 {i} 初始化失败")
                    if attempt == max_retries - 1:
                        self.caps.append(None)
                    time.sleep(1)

    def get_frames(self):
        """获取所有摄像头画面"""
        frames = []
        for i, cap in enumerate(self.caps):
            if cap is None:
                frames.append(None)
                continue

            ret, frame = cap.read()
            if not ret:
                print(f"摄像头 {i} 读取失败，尝试重新初始化...")
                self.reinit_camera(i)
                ret, frame = self.caps[i].read() if self.caps[i] else (False, None)

            frames.append(frame if ret else None)
        return frames

    def reinit_camera(self, index):
        """重新初始化指定摄像头"""
        if index < len(self.caps):
            if self.caps[index]:
                self.caps[index].release()
            self.caps[index] = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not self.caps[index].isOpened():
                print(f"摄像头 {index} 重新初始化失败")
                self.caps[index] = None

    def release_all(self):
        """释放所有资源"""
        for cap in self.caps:
            if cap:
                cap.release()
        self.caps = []


# 使用示例
manager = CameraManager()
try:
    while True:
        frames = manager.get_frames()
        valid_frames = [f for f in frames if f is not None]

        if len(valid_frames) >= 1:  # 只要有至少一个摄像头工作
            # 调整所有画面到相同尺寸
            resized_frames = []
            for frame in valid_frames:
                if frame is not None:
                    resized = cv2.resize(frame, (640 // len(valid_frames), 480))
                    resized_frames.append(resized)

            combined = np.hstack(resized_frames) if len(resized_frames) > 1 else resized_frames[0]
            cv2.imshow('Multi-Camera View', combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    manager.release_all()
    cv2.destroyAllWindows()
