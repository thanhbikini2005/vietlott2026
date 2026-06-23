#!/usr/bin/env python3
"""
Vietlott Lottery Bot - GitHub Actions + Telegram
Tự động quét kết quả xổ số, chọn số theo chiến lược, gửi Telegram
"""
import os, json, random, requests, datetime
from collections import Counter
from pathlib import Path

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")
DATA_FILE = Path("lottery_data.json")

VN_TZ_OFFSET = 7  # UTC+7

# ─── Múi giờ Việt Nam ────────────────────────────────────────────────
def vn_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=VN_TZ_OFFSET)

def vn_date_str(dt=None):
    d = dt or vn_now()
    weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
    return f"{weekdays[d.weekday()]}, {d.strftime('%d/%m/%Y')}"

# ─── Nguồn dữ liệu (nhiều nguồn dự phòng) ───────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*"
}

def fetch_with_fallback(game: str) -> list[int] | None:
    """Thử nhiều nguồn cho từng game, trả về list số trúng hoặc None"""
    fetchers = {
        "mega645":  [_fetch_mega_minhngoc, _fetch_mega_vietlott_api, _fetch_mega_xosovietnam],
        "power655": [_fetch_power_minhngoc, _fetch_power_vietlott_api, _fetch_power_xosovietnam],
        "max3d":    [_fetch_max3d_minhngoc, _fetch_max3d_vietlott_api],
        "lotto535": [_fetch_lotto_minhngoc, _fetch_lotto_vietlott_api],
    }
    for fn in fetchers.get(game, []):
        try:
            result = fn()
            if result:
                return result
        except Exception as e:
            print(f"[WARN] {fn.__name__} failed: {e}")
    return None

# ── MEGA 6/45 ────────────────────────────────────────────────────────
def _fetch_mega_minhngoc():
    r = requests.get("https://www.minhngoc.net.vn/ket-qua-xo-so-dien-toan/mega-645.html", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<td[^>]*class="[^"]*giai[^"]*"[^>]*>(\d{2})</td>', r.text)
    if len(nums) >= 6:
        return list(map(int, nums[:6]))
    return None

def _fetch_mega_vietlott_api():
    today = vn_now().strftime("%Y-%m-%d")
    r = requests.get(f"https://api.vietlott.vn/api/prizeservice/get-prize-info?pageSize=1&pageIndex=0&productId=MEGA&drawDateFrom={today}&drawDateTo={today}", headers=HEADERS, timeout=10)
    data = r.json()
    result_str = data["data"]["items"][0]["awardDetail"]
    nums = json.loads(result_str)["normal"]
    return sorted(nums)

def _fetch_mega_xosovietnam():
    r = requests.get("https://xosovietnam.vn/xo-so-mega-645", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<span[^>]*class="[^"]*ball[^"]*"[^>]*>(\d+)</span>', r.text)
    if len(nums) >= 6:
        return sorted(map(int, nums[:6]))
    return None

# ── POWER 6/55 ──────────────────────────────────────────────────────
def _fetch_power_minhngoc():
    r = requests.get("https://www.minhngoc.net.vn/ket-qua-xo-so-dien-toan/power-655.html", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<td[^>]*class="[^"]*giai[^"]*"[^>]*>(\d{2})</td>', r.text)
    if len(nums) >= 6:
        return list(map(int, nums[:6]))
    return None

def _fetch_power_vietlott_api():
    today = vn_now().strftime("%Y-%m-%d")
    r = requests.get(f"https://api.vietlott.vn/api/prizeservice/get-prize-info?pageSize=1&pageIndex=0&productId=POWER&drawDateFrom={today}&drawDateTo={today}", headers=HEADERS, timeout=10)
    data = r.json()
    result_str = data["data"]["items"][0]["awardDetail"]
    nums = json.loads(result_str)["normal"]
    return sorted(nums)

def _fetch_power_xosovietnam():
    r = requests.get("https://xosovietnam.vn/xo-so-power-655", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<span[^>]*class="[^"]*ball[^"]*"[^>]*>(\d+)</span>', r.text)
    if len(nums) >= 6:
        return sorted(map(int, nums[:6]))
    return None

# ── MAX 3D+ ─────────────────────────────────────────────────────────
def _fetch_max3d_minhngoc():
    r = requests.get("https://www.minhngoc.net.vn/ket-qua-xo-so-dien-toan/max-3d-plus.html", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<td[^>]*class="[^"]*giai[^"]*"[^>]*>(\d{3})</td>', r.text)
    if len(nums) >= 2:
        return list(map(int, nums[:2]))
    return None

def _fetch_max3d_vietlott_api():
    today = vn_now().strftime("%Y-%m-%d")
    r = requests.get(f"https://api.vietlott.vn/api/prizeservice/get-prize-info?pageSize=1&pageIndex=0&productId=MAX3DPLUS&drawDateFrom={today}&drawDateTo={today}", headers=HEADERS, timeout=10)
    data = r.json()
    result_str = data["data"]["items"][0]["awardDetail"]
    pair = json.loads(result_str)["normal"]
    return pair[:2]

# ── LOTTO 5/35 ──────────────────────────────────────────────────────
def _fetch_lotto_minhngoc():
    r = requests.get("https://www.minhngoc.net.vn/ket-qua-xo-so-dien-toan/lotto-535.html", headers=HEADERS, timeout=10)
    import re
    nums = re.findall(r'<td[^>]*class="[^"]*giai[^"]*"[^>]*>(\d{2})</td>', r.text)
    if len(nums) >= 5:
        return list(map(int, nums[:5]))
    return None

def _fetch_lotto_vietlott_api():
    today = vn_now().strftime("%Y-%m-%d")
    r = requests.get(f"https://api.vietlott.vn/api/prizeservice/get-prize-info?pageSize=1&pageIndex=0&productId=LOTTO&drawDateFrom={today}&drawDateTo={today}", headers=HEADERS, timeout=10)
    data = r.json()
    result_str = data["data"]["items"][0]["awardDetail"]
    nums = json.loads(result_str)["normal"]
    return sorted(nums)

# ─── Lịch quay thưởng (Việt Nam) ────────────────────────────────────
DRAW_SCHEDULE = {
    "mega645":  [1, 3, 5],          # T3, T5, T7 (0=Mon)
    "power655": [1, 3, 5],          # T3, T5, T7
    "max3d":    [0, 2, 4],          # T2, T4, T6
    "lotto535": [0, 1, 2, 3, 4],    # T2-T6
}

def has_draw_today(game: str) -> bool:
    wd = vn_now().weekday()
    return wd in DRAW_SCHEDULE.get(game, [])

# ─── Load / Save state ───────────────────────────────────────────────
def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {
        "mega645":  {"history": [], "user_pts": 0, "ai_pts": 0, "draws": 0},
        "power655": {"history": [], "user_pts": 0, "ai_pts": 0, "draws": 0},
        "max3d":    {"history": [], "user_pts": 0, "ai_pts": 0, "draws": 0},
        "lotto535": {"history": [], "user_pts": 0, "ai_pts": 0, "draws": 0},
    }

def save_data(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ─── Phân tích thống kê & chọn số ───────────────────────────────────
def analyze_history(history: list, pick: int, max_num: int, n_quarters: int = 6) -> dict:
    """Phân tích lịch sử: vị trí 1, 2, giữa, cuối-1, cuối"""
    recent = history[-n_quarters * 13:]  # ~2 quý ≈ 26 tuần * pick
    freq = Counter()
    pos_freq = {i: Counter() for i in range(pick)}
    for draw in recent:
        nums = draw["result"][:pick]
        for n in nums:
            freq[n] += 1
        for i, n in enumerate(sorted(nums)):
            pos_freq[i][n] += 1

    hot = [n for n, _ in freq.most_common(max(pick*2, 12))]
    pos_hot = {i: [n for n, _ in pos_freq[i].most_common(3)] or [random.randint(1, max_num)] for i in range(pick)}
    return {"hot": hot, "pos_hot": pos_hot, "freq": dict(freq)}

def pick_user_strategy(analysis: dict, pick: int, max_num: int, n: int = 4) -> list[list[int]]:
    """Chiến lược của người dùng: dùng số nóng theo vị trí"""
    hot = analysis["hot"] or list(range(1, max_num+1))
    pos_hot = analysis["pos_hot"]
    results = []
    for _ in range(n):
        chosen = set()
        # Cố định vị trí đầu, cuối từ thống kê
        for i in range(pick):
            candidates = pos_hot.get(i, hot)
            for c in candidates:
                if c not in chosen:
                    chosen.add(c)
                    break
        # Bổ sung từ hot list
        for h in hot:
            if len(chosen) >= pick:
                break
            chosen.add(h)
        # Điền ngẫu nhiên nếu thiếu
        while len(chosen) < pick:
            chosen.add(random.randint(1, max_num))
        results.append(sorted(chosen)[:pick])
    return results

def pick_ai_strategy(pick: int, max_num: int, analysis: dict, n: int = 4) -> list[list[int]]:
    """Chiến lược AI: cân bằng phân bổ + số nóng + số nguội xen kẽ"""
    hot = analysis["hot"]
    all_nums = list(range(1, max_num+1))
    cold = [n for n in all_nums if n not in hot]
    results = []
    for i in range(n):
        chosen = set()
        # 60% số nóng, 40% số nguội — xen kẽ
        hot_count = int(pick * 0.6)
        cold_count = pick - hot_count
        sample_hot = random.sample(hot[:max(pick, len(hot))], min(hot_count, len(hot)))
        sample_cold = random.sample(cold, min(cold_count, len(cold)))
        chosen = set(sample_hot + sample_cold)
        while len(chosen) < pick:
            chosen.add(random.randint(1, max_num))
        results.append(sorted(chosen)[:pick])
    return results

# ─── Tính điểm & giải ───────────────────────────────────────────────
PRIZE_TABLE = {
    6: {6: ("Đặc biệt", 10), 5: ("Giải 1", 4), 4: ("Giải 4", 2), 3: ("Giải 5", 1)},
    5: {5: ("Đặc biệt", 10), 4: ("Giải 1", 3), 3: ("Giải 4", 1)},
    3: {3: ("Đặc biệt", 5), 2: ("Giải 2", 2)},
}

def score_pick(pick: list[int], result: list[int], pick_size: int) -> tuple[int, str]:
    matches = len(set(pick) & set(result))
    table = PRIZE_TABLE.get(pick_size, {})
    if matches in table:
        label, pts = table[matches]
        return pts, f"{label} (khớp {matches})"
    return 0, f"khớp {matches}"

# ─── Gửi Telegram ────────────────────────────────────────────────────
def send_telegram(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("[TELEGRAM] Chưa cấu hình token/chat_id")
        print(text)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, json=payload, timeout=10)
    if not r.ok:
        print(f"[TG ERROR] {r.text}")

def fmt_nums(nums: list[int]) -> str:
    return " · ".join(f"{n:02d}" for n in nums)

def fmt_pick_line(label: str, pick: list[int], result: list[int], pts: int, note: str) -> str:
    hit = set(result)
    parts = [f"<b>{n:02d}</b>" if n in hit else f"{n:02d}" for n in pick]
    nums_str = " · ".join(parts)
    if pts > 0:
        return f"  {label}: {nums_str} → ✅ {note} (+{pts}đ)"
    else:
        return f"  {label}: {nums_str} → ❌ {note}"

# ─── Xử lý từng game ─────────────────────────────────────────────────
GAME_CONFIG = {
    "mega645":  {"name": "MEGA 6/45",  "emoji": "🔵", "pick": 6, "max": 45},
    "power655": {"name": "POWER 6/55", "emoji": "🟡", "pick": 6, "max": 55},
    "max3d":    {"name": "MAX 3D+",    "emoji": "🟢", "pick": 3, "max": 9},
    "lotto535": {"name": "LOTTO 5/35", "emoji": "🩷", "pick": 5, "max": 35},
}

def process_game(game_id: str, data: dict) -> str | None:
    cfg = GAME_CONFIG[game_id]
    gdata = data[game_id]
    pick = cfg["pick"]
    max_num = cfg["max"]

    # Kiểm tra hôm nay có quay không
    if not has_draw_today(game_id):
        return None

    # Lấy kết quả
    result = fetch_with_fallback(game_id)
    if not result:
        return None

    # Kiểm tra đã xử lý kỳ này chưa (tránh gửi trùng)
    today_str = vn_now().strftime("%d/%m/%Y")
    if gdata["history"] and gdata["history"][-1].get("date") == today_str:
        return None  # Đã xử lý hôm nay

    # Phân tích lịch sử
    analysis = analyze_history(gdata["history"], pick, max_num)

    # Chọn số
    user_picks = pick_user_strategy(analysis, pick, max_num, n=4)
    ai_picks   = pick_ai_strategy(pick, max_num, analysis, n=4)

    # Tính điểm
    user_pts_this = 0
    ai_pts_this   = 0
    lines = []

    lines.append(f"\n{cfg['emoji']} <b>{cfg['name']}</b>")
    lines.append(f"Kết quả: <code>{fmt_nums(result)}</code>")
    lines.append("👤 Dãy của bạn (chiến lược nóng):")
    for i, p in enumerate(user_picks):
        pts, note = score_pick(p, result, pick)
        user_pts_this += pts
        lines.append(fmt_pick_line(f"B{i+1}", p, result, pts, note))
    lines.append("🤖 Dãy AI (chiến lược phân tán):")
    for i, p in enumerate(ai_picks):
        pts, note = score_pick(p, result, pick)
        ai_pts_this += pts
        lines.append(fmt_pick_line(f"A{i+1}", p, result, pts, note))

    gdata["user_pts"] += user_pts_this
    gdata["ai_pts"]   += ai_pts_this
    gdata["draws"]    += 1
    gdata["history"].append({
        "date": today_str,
        "result": result,
        "user_picks": user_picks,
        "ai_picks": ai_picks,
        "user_pts": user_pts_this,
        "ai_pts": ai_pts_this,
    })
    gdata["history"] = gdata["history"][-60:]  # Giữ 60 kỳ gần nhất

    u, a = user_pts_this, ai_pts_this
    winner = "👤 Bạn thắng kỳ này!" if u > a else "🤖 AI thắng kỳ này!" if a > u else "Hòa kỳ này"
    lines.append(f"📊 Kỳ này: Bạn <b>{u}đ</b> | AI <b>{a}đ</b> — {winner}")

    return "\n".join(lines)

# ─── Main ─────────────────────────────────────────────────────────────
def main():
    data = load_data()
    now = vn_now()
    sections = []

    for game_id in ["mega645", "power655", "max3d", "lotto535"]:
        section = process_game(game_id, data)
        if section:
            sections.append(section)

    if not sections:
        print("[INFO] Không có game nào quay hôm nay hoặc chưa có kết quả mới.")
        return

    # Tổng điểm
    total_u = sum(data[g]["user_pts"] for g in data)
    total_a = sum(data[g]["ai_pts"]   for g in data)
    diff = total_u - total_a
    leader = f"👤 Bạn dẫn +{diff}đ ⚠️" if diff > 0 else f"🤖 AI dẫn +{abs(diff)}đ" if diff < 0 else "Đang hòa"

    msg_parts = [
        f"🎰 <b>BOT XỔ SỐ VIETLOTT</b>",
        f"📅 {vn_date_str(now)} — {now.strftime('%H:%M')}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    msg_parts.extend(sections)
    msg_parts += [
        "\n━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>TỔNG ĐIỂM TÍCH LŨY</b>",
        f"👤 Bạn: <b>{total_u}đ</b>   🤖 AI: <b>{total_a}đ</b>",
        f"{leader}",
        f"\n⏰ Quét tiếp: {(now + datetime.timedelta(hours=1)).strftime('%H:%M')} {vn_date_str(now)}",
    ]

    save_data(data)
    send_telegram("\n".join(msg_parts))
    print("[OK] Đã gửi Telegram!")

if __name__ == "__main__":
    main()
