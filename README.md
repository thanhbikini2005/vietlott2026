# 🎰 Vietlott Lottery Bot

Bot tự động quét kết quả xổ số Vietlott, chọn số theo chiến lược, gửi Telegram mỗi giờ.

## Cài đặt (5 bước)

### 1. Tạo Telegram Bot
- Nhắn @BotFather trên Telegram → `/newbot`
- Lưu **Bot Token** (dạng `1234567890:ABC...`)
- Nhắn bot 1 tin bất kỳ, rồi vào:
  `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Lấy **chat_id** từ JSON trả về

### 2. Fork / tạo repo GitHub
- Tạo repo mới hoặc fork repo này
- Copy toàn bộ file vào repo

### 3. Thêm Secrets vào GitHub
Vào `Settings → Secrets and variables → Actions → New repository secret`:

| Secret Name | Giá trị |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID của bạn |

### 4. Bật GitHub Actions
- Vào tab **Actions** → Enable workflows

### 5. Test thủ công
- Vào **Actions → Vietlott Lottery Bot → Run workflow**

## Lịch chạy
Bot chạy mỗi giờ từ **18:00 đến 22:00** giờ VN.  
Chỉ gửi Telegram khi có kết quả mới trong ngày.

## Hệ thống điểm
| Khớp | Mega/Power | Lotto | Max 3D+ |
|------|-----------|-------|---------|
| 6/5/3 số | +10đ (ĐB) | +10đ | +5đ |
| 5/4 số | +4đ / +3đ | +3đ | - |
| 4/3 số | +2đ / +1đ | +1đ | +2đ |

Người dẫn trước **2 điểm** → cảnh báo "AI sắp bị xóa" 😄

## Chiến lược chọn số

**Dãy của bạn (B1-B4):** Thống kê tần suất từng vị trí (đầu, giữa, cuối) trong 2 quý gần nhất, ưu tiên số nóng theo vị trí.

**Dãy AI (A1-A4):** Kết hợp 60% số nóng + 40% số nguội, phân bổ đều ba vùng (thấp/giữa/cao), thêm yếu tố ngẫu nhiên có trọng số.
