import nest_asyncio
import asyncio
import pytz
from gtts import gTTS
import os
import pygame
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from datetime import datetime, timedelta

# Áp dụng nest_asyncio để hỗ trợ nhiều vòng lặp sự kiện trong cùng một môi trường
nest_asyncio.apply()

# Token bot Telegram của bạn
TELEGRAM_TOKEN = '7730208839:AAEi0GkQ23N6TJeeWwCaA2mxSs7v-xdbc8w'

# Từ điển lưu trữ các tác vụ lời nhắc cho từng người dùng
reminder_tasks = {}

# Hàm để phát âm lời nhắn bằng Google TTS
def speak(message: str):
    pygame.mixer.quit()  # Đảm bảo mixer được đóng lại trước khi khởi tạo mới
    pygame.mixer.init()  # Khởi tạo lại mixer cho mỗi lần phát âm thanh
    tts = gTTS(text=message, lang='vi')
    tts.save("message.mp3")
    pygame.mixer.music.load("message.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    os.remove("message.mp3")

# Hàm hủy lời nhắc
async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    # Hủy tác vụ nếu tồn tại
    if user_id in reminder_tasks:
        task = reminder_tasks.pop(user_id)
        task.cancel()
        await query.edit_message_text("Lời nhắc đã bị hủy thành công!")
    else:
        await query.edit_message_text("Không có lời nhắc nào để hủy!")

# Hàm đặt lời nhắc và thời gian hẹn
async def nhacnho(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Lấy thời gian hẹn và thông điệp
        reminder_time_str = context.args[0]  # Ví dụ: "15:30"
        reminder_message = " ".join(context.args[1:])  # Ví dụ: "Hãy uống nước"

        # Chuyển đổi thời gian hẹn thành đối tượng datetime
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(tz)

        # Parse giờ phút từ chuỗi
        reminder_hour, reminder_minute = map(int, reminder_time_str.split(":"))
        
        # Tạo datetime cho thời gian hẹn
        reminder_time = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)

        # Nếu thời gian hẹn đã qua trong ngày, đặt hẹn cho ngày mai
        if reminder_time < now:
            reminder_time += timedelta(days=1)

        # Tính thời gian còn lại cho lời nhắc
        user_id = update.message.from_user.id

        # Hủy lời nhắc trước đó nếu có
        if user_id in reminder_tasks:
            reminder_tasks[user_id].cancel()

        # Gửi thông báo và nút hủy
        keyboard = [
            [InlineKeyboardButton("Hủy lời nhắc", callback_data="cancel_reminder")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Lời nhắc đã được thiết lập cho: {reminder_time.strftime('%H:%M:%S %d/%m/%Y')}.\nLời nhắn: {reminder_message}",
            reply_markup=reply_markup
        )

        # Tác vụ chờ đến giờ hẹn
        async def reminder_task():
            await asyncio.sleep((reminder_time - now).total_seconds())
            await update.message.reply_text(f"Đến giờ! Lời nhắc: {reminder_message}")
            speak(reminder_message)

        # Lưu tác vụ vào từ điển
        task = asyncio.create_task(reminder_task())
        reminder_tasks[user_id] = task

    except IndexError:
        await update.message.reply_text("Bạn cần nhập thời gian và lời nhắn. Ví dụ: /nhacnho 15:30 Hãy uống nước")

# Hàm main để khởi động ứng dụng
async def main() -> None:
    # Tạo ứng dụng bot với token của bạn
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Đăng ký handler cho các lệnh
    application.add_handler(CommandHandler("nhacnho", nhacnho))  # Lệnh nhacnho
    application.add_handler(CallbackQueryHandler(cancel_reminder, pattern="^cancel_reminder$"))  # Lệnh hủy

    # Chạy bot với polling
    await application.run_polling()

# Nếu đang chạy trong môi trường mà vòng lặp sự kiện đã được khởi tạo, chỉ cần gọi hàm main
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
