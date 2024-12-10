import cv2
import numpy as np
import requests
from ultralytics import YOLO
import asyncio
import aiohttp
import time
from queue import Queue
import threading
import os
from datetime import datetime

# Telegram token và chat ID
TELEGRAM_TOKEN = '7730208839:AAEi0GkQ23N6TJeeWwCaA2mxSs7v-xdbc8w'
CHAT_ID = '7376449966'

# Tải mô hình YOLOv8
model = YOLO('yolov8l-pose.pt')

# URL của camera video stream
video_url = "http://172.20.10.8:5000/video_feed"

# Danh sách màu sắc để sử dụng cho các hộp
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), 
          (0, 255, 255), (255, 0, 255), (192, 192, 192), (128, 0, 128), 
          (128, 128, 0), (0, 128, 128)]  # Thêm nhiều màu sắc nếu cần

# Queue để lưu các tin nhắn cần gửi
message_queue = Queue()
previous_posture = None
video_duration = 10  # Thời gian ghi video (giây)
last_message_time = 0  # Thời gian gửi tin nhắn cuối cùng
last_video_time = 0  # Thời gian ghi video cuối cùng
recording = False  # Trạng thái quay video

# Tạo một Lock để đồng bộ truy cập camera
cap_lock = threading.Lock()

async def send_telegram_message(posture, file_path=None, is_video=True):
    # Hàm gửi tin nhắn đến Telegram
    timestamp = datetime.now().strftime("%H:%M:%S, %d/%m/%Y")
    message = f"Phát hiện chuyển động bất thường: {posture} : {timestamp}"
    async with aiohttp.ClientSession() as session:
        await session.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            data={'chat_id': CHAT_ID, 'text': message}
        )
        if file_path:
            with open(file_path, 'rb') as file:
                if is_video:
                    await session.post(
                        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo',
                        data={'chat_id': CHAT_ID, 'video': file}
                    )
                else:
                    await session.post(
                        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto',
                        data={'chat_id': CHAT_ID, 'photo': file}
                    )

def message_sender():
    while True:
        # Chờ nhận tin nhắn từ queue
        posture, file_path, is_video = message_queue.get()
        asyncio.run(send_telegram_message(posture, file_path, is_video))
        message_queue.task_done()

def capture_image(frame):
    # Chụp ảnh và lưu vào tệp
    image_path = "detected_posture.jpg"
    cv2.imwrite(image_path, frame)
    return image_path

def record_video(cap):
    global recording
    recording = True
    video_path = "detected_motion.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))

    start_time = time.time()
    while recording and (time.time() - start_time < video_duration):
        with cap_lock:  # Ensure only one thread accesses the camera at a time
            ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    out.release()
    recording = False
    return video_path

async def process_frame():
    global previous_posture, last_message_time, last_video_time, cap

    # Mở kết nối đến MJPEG stream bằng requests
    stream = requests.get(video_url, stream=True)
    bytes_data = b''  # Buffer để lưu trữ dữ liệu từ stream

    # Mở camera video
    cap = cv2.VideoCapture(video_url)

    while True:
        bytes_data += stream.raw.read(1024)
        a = bytes_data.find(b'\xff\xd8')  # JPEG bắt đầu
        b = bytes_data.find(b'\xff\xd9')  # JPEG kết thúc

        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]  # Lấy dữ liệu JPEG
            bytes_data = bytes_data[b+2:]  # Cập nhật lại buffer
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

            # Dự đoán tư thế
            results = model(frame)

            # Duyệt qua từng kết quả phát hiện
            for i, result in enumerate(results):  
                if result.keypoints is not None:
                    # Lấy keypoints
                    keypoints = result.keypoints.xy  # Sử dụng thuộc tính xy để lấy tọa độ keypoints
                    
                    # Vẽ hộp xung quanh người phát hiện
                    if result.boxes is not None and len(result.boxes) > 0:
                        bbox = result.boxes.xyxy[0]  # Lấy hộp xung quanh đầu tiên
                        x1, y1, x2, y2 = map(int, bbox.tolist())
                        color = colors[i % len(colors)]  # Chọn màu cho mỗi người
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)  # Vẽ hộp xung quanh người

                    # Kiểm tra tư thế
                    if keypoints[0].shape[0] > 11:  # Đảm bảo có đủ keypoints để truy cập
                        torso_y = keypoints[0][2][1].item()  # Y vị trí của torso (keypoint thứ 2)
                        hip_y = keypoints[0][11][1].item()    # Y vị trí của hip (keypoint thứ 11)
                        if torso_y < hip_y:
                            posture = "Standing"
                        else:
                            posture = "Lying Down"

                        # Kiểm tra khoảng thời gian giữa các thay đổi tư thế
                        current_time = time.time()
                        if posture != previous_posture:
                            time_diff = current_time - last_message_time
                            
                            # Nếu khoảng cách giữa các thay đổi tư thế nhỏ hơn 0.5 giây, chụp ảnh
                            if time_diff < 0.5:
                                image_path = capture_image(frame)
                                message_thread = threading.Thread(target=lambda: message_queue.put((posture, image_path, False)))
                                message_thread.start()
                            # Nếu khoảng cách giữa các thay đổi tư thế lớn hơn hoặc bằng 0.5 giây, quay video
                            elif time_diff >= 0.5 and (current_time - last_video_time >= video_duration):
                                video_thread = threading.Thread(target=lambda: message_queue.put((posture, record_video(cap), True)))
                                video_thread.start()

                            previous_posture = posture  # Cập nhật tư thế trước đó
                            last_message_time = current_time  # Cập nhật thời gian gửi tin nhắn
                            last_video_time = current_time  # Cập nhật thời gian ghi video

                    # Hiển thị tư thế
                    cv2.putText(frame, posture, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Hiển thị khung hình
            cv2.imshow('Pose Detection', frame)

            # Nhấn 'q' để thoát
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # Giải phóng tài nguyên
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    # Tạo và khởi động luồng gửi tin nhắn
    threading.Thread(target=message_sender, daemon=True).start()

    # Chạy hàm xử lý khung hình với tham số cap
    asyncio.run(process_frame())
