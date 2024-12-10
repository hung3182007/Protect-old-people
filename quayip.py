import cv2
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import os

# Thông tin bot Telegram
BOT_TOKEN = "7730208839:AAEi0GkQ23N6TJeeWwCaA2mxSs7v-xdbc8w"  # Thay bằng token bot của bạn
CHAT_ID = "7376449966"  # Thay bằng chat ID của bạn
bot = telebot.TeleBot(BOT_TOKEN)

# Hàm quay video từ camera IP
def record_video(duration, chat_id):
    cap = cv2.VideoCapture("http://172.20.10.8:5000/video_feed")  # Sử dụng camera IP
    if not cap.isOpened():
        bot.send_message(chat_id, "Không thể mở camera!")
        return

    # Tạo tên file video
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = f"video_{timestamp}.mp4"

    # Lấy thông số video
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 8  # Giảm tốc độ khung hình xuống còn 15 FPS để camera kịp gửi dữ liệu
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Bộ mã hóa video cho định dạng MP4
    out = cv2.VideoWriter(video_path, fourcc, fps, (frame_width, frame_height))

    # Đảm bảo camera ổn định
    time.sleep(2)  # Chờ 2 giây cho camera ổn định

    # Quay video trong thời gian quy định
    start_time = time.time()
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()

    # Gửi video tới Telegram
    with open(video_path, "rb") as video_file:
        bot.send_video(chat_id, video_file)

    # Xóa file video sau khi gửi
    os.remove(video_path)

# Hàm xử lý lệnh /quayvideo
@bot.message_handler(commands=['quayvideo'])
def handle_quayvideo(message):
    chat_id = message.chat.id

    # Tạo giao diện các nút chọn thời gian
    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("10 giây", callback_data="record_10"),
        InlineKeyboardButton("30 giây", callback_data="record_30"),
        InlineKeyboardButton("1 phút", callback_data="record_60"),
        InlineKeyboardButton("5 phút", callback_data="record_300"),
        InlineKeyboardButton("10 phút", callback_data="record_600"),
        InlineKeyboardButton("30 phút", callback_data="record_1800"),
    ]
    markup.add(*buttons)

    bot.send_message(chat_id, "Chọn thời gian quay video:", reply_markup=markup)

# Xử lý khi nhấn vào các nút thời gian
@bot.callback_query_handler(func=lambda call: call.data.startswith("record_"))
def handle_record_callback(call):
    chat_id = call.message.chat.id
    duration = int(call.data.split("_")[1])  # Lấy thời gian từ callback_data

    bot.send_message(chat_id, f"Đang quay video trong {duration // 60} phút {duration % 60} giây...")
    
    # Quay video trong luồng riêng để không làm gián đoạn bot
    threading.Thread(target=record_video, args=(duration, chat_id)).start()

# Chạy bot
if __name__ == "__main__":
    print("Bot đang chạy...")
    bot.infinity_polling()
