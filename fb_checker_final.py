import requests
import telegram
import time
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from urllib.parse import urlparse

# =======================================================
#               1. CẤU HÌNH BẮT BUỘC (CẬP NHẬT TẠI ĐÂY)
# =======================================================
BOT_TOKEN = "8170628944:AAFgSld7haAF0n8Y5kMamDYWtQkTSsKb_dA" # <-- THAY BẰNG TOKEN CỦA BẠN
# CHAT_ID Tùy chọn (được dùng để giới hạn người dùng có quyền admin)
ADMIN_CHAT_ID = 7123827128           # <-- THAY BẰNG CHAT ID CỦA BẠN (Sử dụng số nguyên - không dùng chuỗi "")

# =======================================================
#               2. CẤU HÌNH HỆ THỐNG
# =======================================================
INPUT_FILE = "check_list.txt"
CHECK_INTERVAL = 5 # Thời gian chờ giữa các lần check (giây)
TIMEOUT = 15       # Timeout cho mỗi yêu cầu HTTP (giây)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
}

# --- CÁC HÀM XỬ LÝ LƯU TRỮ ---

def read_links():
    """Đọc danh sách link/UID hiện tại từ file."""
    if not os.path.exists(INPUT_FILE):
        return set()
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        # Sử dụng set để đảm bảo không có link trùng lặp
        return {line.strip() for line in f if line.strip()}

def write_links(links_set):
    """Ghi danh sách link/UID mới vào file."""
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        for link in sorted(list(links_set)):
            f.write(link + '\n')

def normalize_input(raw_input):
    """Chuẩn hóa UID/Link (Hàm này giữ nguyên từ bot cũ)."""
    link = raw_input.strip()
    if not link: return None
    if link.isdigit() and len(link) > 10:
        return link # Trả về UID thô để dễ dàng quản lý trong file
    if 'facebook.com' in link or 'fb.com' in link:
        return link
    return None

def check_link_status(link):
    """Gửi yêu cầu HTTP GET để kiểm tra trạng thái công khai (Hàm này giữ nguyên)."""
    # Nếu là UID, ta chuyển thành URL để check
    check_url = f"https://www.facebook.com/profile.php?id={link}" if link.isdigit() and len(link) > 10 else link
    
    try:
        response = requests.get(check_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            if 'login.php' in response.url or 'checkpoint' in response.text or 'Bạn phải đăng nhập' in response.text:
                return "BLOCKED/LOGIN_REQUIRED" 
            return "LIVE"
        elif response.status_code == 404:
            return "DIE"
        else:
            return f"UNKNOWN (Status: {response.status_code})"
    except requests.exceptions.Timeout:
        return "ERROR_TIMEOUT" 
    except requests.exceptions.ConnectionError:
        return "ERROR_CONNECTION" 
    except Exception as e:
        return f"ERROR_OTHER ({type(e).__name__})"

# --- CÁC HÀM XỬ LÝ LỆNH TELEGRAM ---

async def check_admin(update: Update):
    """Kiểm tra quyền admin dựa trên CHAT_ID."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Bạn không có quyền thực hiện lệnh này.")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start."""
    await update.message.reply_text(
        f"Xin chào {update.effective_user.first_name}!\n"
        "Bot đã sẵn sàng.\n\n"
        "Các lệnh quản lý:\n"
        "👉 /add [link/uid]: Thêm vào danh sách.\n"
        "👉 /remove [link/uid]: Xóa khỏi danh sách.\n"
        "👉 /list: Xem danh sách hiện tại.\n"
        "👉 /check: Chạy kiểm tra tất cả mục (Chỉ admin).\n"
    )

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /add [link/uid]."""
    if not await check_admin(update): return

    if not context.args:
        await update.message.reply_text("Cú pháp: /add [link hoặc uid]")
        return

    raw_input = context.args[0]
    normalized = normalize_input(raw_input)

    if not normalized:
        await update.message.reply_text("❌ Input không hợp lệ. Vui lòng nhập UID (chỉ số) hoặc Link FB.")
        return
        
    links = read_links()
    if normalized in links:
        await update.message.reply_text(f"⚠️ `{normalized}` đã có trong danh sách.")
    else:
        links.add(normalized)
        write_links(links)
        await update.message.reply_text(f"✅ Đã thêm `{normalized}` vào danh sách.")

async def remove_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /remove [link/uid]."""
    if not await check_admin(update): return

    if not context.args:
        await update.message.reply_text("Cú pháp: /remove [link hoặc uid]")
        return
        
    raw_input = context.args[0]
    normalized = normalize_input(raw_input)

    if not normalized:
        await update.message.reply_text("❌ Input không hợp lệ. Vui lòng nhập UID (chỉ số) hoặc Link FB.")
        return

    links = read_links()
    if normalized in links:
        links.remove(normalized)
        write_links(links)
        await update.message.reply_text(f"✅ Đã xóa `{normalized}` khỏi danh sách.")
    else:
        await update.message.reply_text(f"⚠️ `{normalized}` không có trong danh sách.")

async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /list."""
    links = read_links()
    if not links:
        await update.message.reply_text("Danh sách kiểm tra hiện đang trống.")
        return

    link_list_str = "\n".join(sorted(list(links)))
    message = f"📋 **DANH SÁCH KIỂM TRA ({len(links)} mục):**\n```\n{link_list_str}\n```"
    await update.message.reply_text(message, parse_mode=telegram.ParseMode.MARKDOWN)

async def check_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /check: Chạy toàn bộ quá trình kiểm tra."""
    if not await check_admin(update): return
    
    links = read_links()
    if not links:
        await update.message.reply_text("⚠️ Danh sách trống, không có gì để kiểm tra.")
        return

    await update.message.reply_text(f"⚙️ Bắt đầu kiểm tra **{len(links)}** mục. Vui lòng chờ...")

    live_count = 0
    die_count = 0
    unknown_count = 0
    
    # Thực hiện kiểm tra
    for i, link in enumerate(links):
        status = check_link_status(link)
        
        if status == "LIVE":
            live_count += 1
        elif status == "DIE":
            die_count += 1
            await update.message.reply_text(f"🔴 **DIE** | ({i+1}/{len(links)}) | `{link}`", parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            unknown_count += 1
            await update.message.reply_text(f"🟡 **{status}** | ({i+1}/{len(links)}) | `{link}`", parse_mode=telegram.ParseMode.MARKDOWN)
        
        time.sleep(CHECK_INTERVAL)

    # Báo cáo tổng kết
    summary_msg = f"""
🏁 **KIỂM TRA HOÀN TẤT**
Tổng cộng: **{len(links)}** mục
- LIVE (Công khai): **{live_count}**
- DIE (Không tồn tại): **{die_count}**
- Lỗi/Không xác định: **{unknown_count}**
    """
    await update.message.reply_text(summary_msg, parse_mode=telegram.ParseMode.MARKDOWN)


def main():
    """Hàm chính để khởi tạo và chạy bot Telegram."""
    try:
        # Khởi tạo Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Thêm các trình xử lý lệnh
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("add", add_link))
        application.add_handler(CommandHandler("remove", remove_link))
        application.add_handler(CommandHandler("list", list_links))
        application.add_handler(CommandHandler("check", check_all_links))

        print("--- FB MANAGER BOT ĐANG CHẠY ---")
        print(f"Admin CHAT ID: {ADMIN_CHAT_ID}")
        print("Bot đang lắng nghe các lệnh từ Telegram...")
        
        # Chạy bot (lắng nghe liên tục)
        application.run_polling(poll_interval=1)
        
    except Exception as e:
        print(f"LỖI KHỞI TẠO BOT: {e}")

if __name__ == "__main__":
    main()
