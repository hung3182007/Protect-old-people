from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt

# Đường dẫn tới mô hình và ảnh
model_path = "yolov8l-pose.pt"
image_path = r"C:\\Users\\nguye\\Downloads\\2.jpg"

# Tải mô hình
model = YOLO(model_path)

# Dự đoán trên ảnh
results = model(image_path)

# Lấy kết quả đầu tiên (nếu có nhiều hình ảnh, chỉ lấy hình đầu tiên)
result_image = results[0].plot()

# Hiển thị kết quả
plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
plt.axis("off")
plt.title("Kết quả phát hiện với YOLOv8l-pose")
plt.show()

# Lưu kết quả vào file nếu cần
output_path = r"C:\\Users\\nguye\\Downloads\\2s.jpg"
cv2.imwrite(output_path, result_image)
print(f"Kết quả đã được lưu tại: {output_path}")
