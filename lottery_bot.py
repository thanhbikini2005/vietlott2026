#!/usr/bin/env python3
"""
Vietlott Lottery Bot v2
Nguồn data: github.com/googlesky/vietlott-data (hoạt động từ GitHub Actions)
Backup: github.com/NhanAZ-Drops/vietlott-data-research
"""
import os, json, random, requests, datetime
from collections import Counter
from pathlib import Path

TG_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT   = os.environ.get("TELEGRAM_CHAT_ID", "")
DATA_FILE = Path("lottery_data.json")
BASE_URL  = "https://raw.githubusercontent.com/googlesky/vietlott-data/main/data"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VietlottBot/2.0)"}

# ── Múi giờ VN ──────────────────────────────────────────────────────
def vn_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)

def vn_weekday_str(dt=None):
    d = dt or vn_now()
    days = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
    return f"{days[d.weekday()]}, {d.strftime('%d/%m/%Y')}"

# ── Cấu hình game ────────────────────────────────────────────────────
# Lịch thật từ data thực tế:
# Mega 6/45   -> power645.jsonl  -> T4, T6, CN  (weekday 2,4,6)
# Power 6/55  -> power655.jsonl  -> T3, T5, T7  (weekday 1,3,5)
# Max 3D+     -> max3d.jsonl     -> T2, T4, T6  (weekday 0,2,4)
# Lotto 5/35  -> lotto535.jsonl  -> hằng ngày
GAMES = {
    "mega645": {
        "name": "MEGA 6/45", "emoji": "🔵",
        "file": "power645.jsonl",
        "pick": 6, "max": 45,
        "draw_days": [2, 4, 6],   # T4, T6, CN
        "backup_file": None,
    },
    "power655": {
        "name": "POWER 6/55", "emoji": "🟡",
        "file": "power655.jsonl",
        "pick": 6, "max": 55,
        "draw_days": [1, 3, 5],   # T3, T5, T7
        "backup_file": None,
    },
    "max3d": {
        "name": "MAX 3D+", "emoji": "🟢",
        "file": "max3d.jsonl",
        "pick": 3, "max": 9,
        "draw_days": [0, 2, 4],   # T2, T4, T6
        "is_3d": True,
        "backup_file": "max3d_pro.jsonl",
    },
    "lotto535": {
        "name": "LOTTO 5/35", "emoji": "🩷",
        "file": "lotto535.jsonl",
        "pick": 5, "max": 35,
        "draw_days": list(range(7)),  # Hằng ngày
        "backup_file": None,
    },
}

# ── Lấy data từ GitHub ───────────────────────────────────────────────
def fetch_jsonl(filename: str) -> list[dict]:
    url = f"{BASE_URL}/{filename}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    lines = [json.loads(l) for l in r.text.strip().split("\n") if l.strip()]
    return lines

def get_latest_result(game_id: str) -> dict | None:
    """Lấy kết quả kỳ mới nhất, kiểm tra đúng ngày hôm nay"""
    cfg = GAMES[game_id]
    today = vn_now().strftime("%Y-%m-%d")

    for fname in [cfg["file"], cfg.get("backup_file")]:
        if not fname:
            continue
        try:
            records = fetch_jsonl(fname)
            # Lấy tất cả kỳ của hôm nay
            today_records = [r for r in records if r["date"] == today]
            if today_records:
                return today_records[-1]  # Kỳ cuối nhất hôm nay
        except Exception as e:
            print(f"[WARN] fetch {fname}: {e}")

    return None

def get_history_results(game_id: str, n_weeks: int = 26) -> list[list[int]]:
    """Lấy lịch sử ~2 quý để thống kê"""
    cfg = GAMES[game_id]
    try:
        records = fetch_jsonl(cfg["file"])
        cutoff = (vn_now() - datetime.timedelta(weeks=n_weeks)).strftime("%Y-%m-%d")
        recent = [r for r in records if r["date"] >= cutoff]
        results = []
        for r in recent:
            raw = r["result"]
            if cfg.get("is_3d"):
                # Max 3D: lấy 2 số đầu, parse thành int
                nums = [int(x) % 1000 for x in raw[:2]]
            else:
                nums = [int(x) for x in raw[:cfg["pick"]]]
            results.append(nums)
        return results
    except Exception as e:
        print(f"[WARN] history {game_id}: {e}")
        return []

# ── Load / Save state ────────────────────────────────────────────────
def load_state() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    default = {}
    for g in GAMES:
        default[g] = {"user_pts": 0, "ai_pts": 0, "draws": 0,
                       "last_date": "", "history_pts": []}
    return default

def save_state(state: dict):
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

# ── Phân tích & chọn số ──────────────────────────────────────────────
def analyze_3d(history_raw: list, all_records: list) -> dict:
    """Phân tích lịch sử Max 3D+: tìm các bộ số 3 chữ số hay ra"""
    freq = Counter()
    for r in all_records[-200:]:
        for x in r.get("result", []):
            freq[str(x).zfill(3)] += 1
    hot_3d = [n for n, _ in freq.most_common(50)]
    return {"hot_3d": hot_3d, "hot": [], "pos_hot": {}}

def analyze(history: list[list[int]], pick: int, max_num: int) -> dict:
    if not history:
        return {"hot": list(range(1, max_num+1)), "pos_hot": {}}

    freq = Counter()
    pos_freq = {i: Counter() for i in range(pick)}
    for nums in history:
        s = sorted(nums[:pick])
        for n in s:
            freq[n] += 1
        for i, n in enumerate(s):
            pos_freq[i][n] += 1

    hot = [n for n, _ in freq.most_common(max(pick*2, 14))]
    pos_hot = {}
    for i in range(pick):
        top = [n for n, _ in pos_freq[i].most_common(5)]
        pos_hot[i] = top if top else hot[:5]

    return {"hot": hot, "pos_hot": pos_hot}

def user_picks(analysis: dict, pick: int, max_num: int, is_3d=False) -> list[list[int]]:
    """4 dãy theo chiến lược người dùng: hot number + vị trí thống kê"""
    if is_3d:
        return _user_picks_3d(analysis)
    hot = analysis["hot"]
    pos_hot = analysis["pos_hot"]
    results = []
    for attempt in range(4):
        chosen = set()
        for i in range(pick):
            candidates = pos_hot.get(i, hot)
            for c in candidates:
                if c not in chosen:
                    chosen.add(c)
                    break
        for h in hot:
            if len(chosen) >= pick:
                break
            chosen.add(h)
        while len(chosen) < pick:
            chosen.add(random.randint(1, max_num))
        base = sorted(chosen)[:pick]
        if attempt > 0 and len(hot) > pick:
            base = sorted(set(hot[attempt:attempt+pick]))
            while len(base) < pick:
                base.append(random.randint(1, max_num))
            base = sorted(set(base))[:pick]
        results.append(base)
    return results

def _user_picks_3d(analysis: dict) -> list[list[str]]:
    """4 bộ số 3 chữ số cho Max 3D+, dùng hot digit patterns"""
    hot_3d = analysis.get("hot_3d", [])
    results = []
    for _ in range(4):
        if len(hot_3d) >= 3:
            sample = random.sample(hot_3d[:20], min(3, len(hot_3d)))
        else:
            sample = [f"{random.randint(0,999):03d}" for _ in range(3)]
        results.append(sample)
    return results

def ai_picks(analysis: dict, pick: int, max_num: int, is_3d=False) -> list[list[int]]:
    if is_3d:
        return _ai_picks_3d()
    """4 dãy theo chiến lược AI: phân tán + xen kẽ nóng/nguội"""
    hot = set(analysis["hot"])
    all_nums = list(range(1, max_num+1))
    cold = [n for n in all_nums if n not in hot]
    hot_list = list(hot)
    results = []

    strategies = [
        # Chiến lược 1: 60% hot, 40% cold
        lambda: _mixed_pick(hot_list, cold, pick, 0.6),
        # Chiến lược 2: trải đều 3 vùng
        lambda: _zone_pick(pick, max_num),
        # Chiến lược 3: chẵn/lẻ cân bằng
        lambda: _balanced_pick(pick, max_num),
        # Chiến lược 4: hot top + 1 surprise
        lambda: _hot_surprise(hot_list, cold, pick, max_num),
    ]
    for fn in strategies:
        results.append(sorted(fn()))
    return results

def _ai_picks_3d() -> list[list[str]]:
    """4 bộ số 3 chữ số cho Max 3D+ - AI random có trọng số"""
    results = []
    for _ in range(4):
        bos = []
        for _ in range(3):
            # Ưu tiên số "đẹp": lặp, mirror, tăng dần
            strategy = random.choice(["repeat","mirror","seq","random"])
            if strategy == "repeat":
                d = random.randint(0,9)
                bos.append(f"{d}{d}{d}")
            elif strategy == "mirror":
                d1, d2 = random.randint(0,9), random.randint(0,9)
                bos.append(f"{d1}{d2}{d1}")
            elif strategy == "seq":
                d = random.randint(0,7)
                bos.append(f"{d}{d+1}{d+2}")
            else:
                bos.append(f"{random.randint(0,999):03d}")
        results.append(bos)
    return results

def _mixed_pick(hot, cold, pick, hot_ratio):
    n_hot = round(pick * hot_ratio)
    n_cold = pick - n_hot
    s = set(random.sample(hot, min(n_hot, len(hot))))
    s.update(random.sample(cold, min(n_cold, len(cold))))
    while len(s) < pick:
        s.add(random.randint(1, max(hot + cold)))
    return list(s)[:pick]

def _zone_pick(pick, max_num):
    z = max_num // pick
    result = set()
    for i in range(pick):
        lo, hi = i*z+1, min((i+1)*z, max_num)
        result.add(random.randint(lo, hi))
    while len(result) < pick:
        result.add(random.randint(1, max_num))
    return list(result)[:pick]

def _balanced_pick(pick, max_num):
    even = [n for n in range(2, max_num+1, 2)]
    odd  = [n for n in range(1, max_num+1, 2)]
    half = pick // 2
    s = set(random.sample(even, half) + random.sample(odd, pick - half))
    while len(s) < pick:
        s.add(random.randint(1, max_num))
    return list(s)[:pick]

def _hot_surprise(hot, cold, pick, max_num):
    n = min(pick-1, len(hot))
    s = set(random.sample(hot, n))
    surprise = random.choice(cold) if cold else random.randint(1, max_num)
    s.add(surprise)
    while len(s) < pick:
        s.add(random.randint(1, max_num))
    return list(s)[:pick]

# ── Tính điểm ────────────────────────────────────────────────────────
def _score_3d(pick_3d: list[str], result_all: list[str]) -> int:
    """Max 3D+: khớp 3 số = 5đ (ĐB), khớp 2 = 2đ, khớp 1 = 1đ"""
    hits = sum(1 for p in pick_3d if p in result_all)
    if hits == 3: return 5
    if hits == 2: return 2
    if hits == 1: return 1
    return 0

PRIZE = {
    6: {6:("Đặc Biệt",10), 5:("Giải 1",4), 4:("Giải 4",2), 3:("Giải 5",1)},
    5: {5:("Đặc Biệt",10), 4:("Giải 1",3), 3:("Giải 4",1)},
    3: {3:("Đặc Biệt",5),  2:("Giải 2",2)},
}

def score(pick_nums: list[int], result: list[int], pick_size: int) -> tuple[int, str]:
    m = len(set(pick_nums) & set(result))
    tbl = PRIZE.get(pick_size, {})
    if m in tbl:
        lbl, pts = tbl[m]
        return pts, f"{lbl} ✅"
    return 0, f"khớp {m}"

# ── Format tin nhắn Telegram ─────────────────────────────────────────
def fmt_nums(nums: list[int]) -> str:
    return " · ".join(f"{n:02d}" for n in nums)

def fmt_row(label: str, pick: list[int], result: list[int], pts: int, note: str) -> str:
    hit = set(result)
    parts = [f"<b>{n:02d}</b>" if n in hit else f"{n:02d}" for n in pick]
    nums_str = " · ".join(parts)
    return f"  {label}: {nums_str} → {note}{' +'+str(pts)+'đ' if pts else ''}"

def build_game_section(game_id: str, result_rec: dict, state: dict) -> str:
    cfg = GAMES[game_id]
    pick = cfg["pick"]
    max_num = cfg["max"]
    is_3d = cfg.get("is_3d", False)

    # Parse kết quả
    raw = result_rec["result"]
    if is_3d:
        # Max 3D+: kết quả là list 3-digit strings, lấy tất cả bộ
        result_3d_all = [str(x).zfill(3) for x in raw]
        result = result_3d_all  # Dùng để so khớp
        result_display = result_3d_all[:6]
    else:
        result = sorted([int(x) for x in raw[:pick]])

    # Lấy lịch sử để phân tích
    history = get_history_results(game_id)
    if is_3d:
        try:
            all_records = fetch_jsonl(cfg["file"])
        except:
            all_records = []
        analysis = analyze_3d(history, all_records)
    else:
        analysis = analyze(history, pick, max_num)

    u_picks = user_picks(analysis, pick, max_num, is_3d=is_3d)
    a_picks  = ai_picks(analysis, pick, max_num, is_3d=is_3d)

    # Tính điểm
    if is_3d:
        u_pts = sum(_score_3d(p, result_3d_all) for p in u_picks)
        a_pts = sum(_score_3d(p, result_3d_all) for p in a_picks)
    else:
        u_pts = sum(score(p, result, pick)[0] for p in u_picks)
        a_pts  = sum(score(p, result, pick)[0] for p in a_picks)

    # Cập nhật state
    g = state[game_id]
    g["user_pts"] += u_pts
    g["ai_pts"]   += a_pts
    g["draws"]    += 1
    g["last_date"] = result_rec["date"]
    g["history_pts"].append({"date": result_rec["date"], "u": u_pts, "a": a_pts})
    g["history_pts"] = g["history_pts"][-60:]

    # Build section text
    lines = [f"\n{cfg['emoji']} <b>{cfg['name']}</b> — Kỳ #{result_rec['id']}"]
    if is_3d:
        lines.append(f"Kết quả: <code>{' · '.join(result_3d_all[:6])}</code> (6 bộ đầu)")
    else:
        lines.append(f"Kết quả: <code>{fmt_nums(result)}</code>")

    lines.append("👤 <i>Dãy của bạn (thống kê nóng):</i>")
    for i, p in enumerate(u_picks):
        if is_3d:
            hits = sum(1 for x in p if x in result_3d_all)
            pts = _score_3d(p, result_3d_all)
            note = f"khớp {hits}" if pts == 0 else ("Đặc Biệt ✅" if hits==3 else f"Giải {4-hits} ✅")
            hl = [f"<b>{x}</b>" if x in result_3d_all else x for x in p]
            lines.append(f"  B{i+1}: {' · '.join(hl)} → {note}{' +'+str(pts)+'đ' if pts else ''}")
        else:
            pts, note = score(p, result, pick)
            lines.append(fmt_row(f"B{i+1}", p, result, pts, note))

    lines.append("🤖 <i>Dãy AI (chiến lược phân tán):</i>")
    for i, p in enumerate(a_picks):
        if is_3d:
            hits = sum(1 for x in p if x in result_3d_all)
            pts = _score_3d(p, result_3d_all)
            note = f"khớp {hits}" if pts == 0 else ("Đặc Biệt ✅" if hits==3 else f"Giải {4-hits} ✅")
            hl = [f"<b>{x}</b>" if x in result_3d_all else x for x in p]
            lines.append(f"  A{i+1}: {' · '.join(hl)} → {note}{' +'+str(pts)+'đ' if pts else ''}")
        else:
            pts, note = score(p, result, pick)
            lines.append(fmt_row(f"A{i+1}", p, result, pts, note))

    winner_str = "👤 Bạn thắng kỳ này!" if u_pts > a_pts else "🤖 AI thắng kỳ này!" if a_pts > u_pts else "Hòa"
    lines.append(f"📊 Kỳ này: Bạn <b>{u_pts}đ</b> | AI <b>{a_pts}đ</b> — {winner_str}")
    lines.append(f"🏅 Tổng tích lũy: Bạn <b>{g['user_pts']}đ</b> | AI <b>{g['ai_pts']}đ</b>")

    return "\n".join(lines)

# ── Gửi Telegram ─────────────────────────────────────────────────────
def send_telegram(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("=== [DRY RUN - không có token] ===")
        print(text)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"}, timeout=10)
    if r.ok:
        print("[OK] Đã gửi Telegram!")
    else:
        print(f"[TG ERROR] {r.status_code}: {r.text[:200]}")

# ── Main ──────────────────────────────────────────────────────────────
def main():
    state = load_state()
    now = vn_now()
    today_str = now.strftime("%Y-%m-%d")
    sections = []

    for game_id, cfg in GAMES.items():
        # Kiểm tra hôm nay có quay không
        if now.weekday() not in cfg["draw_days"]:
            print(f"[SKIP] {cfg['name']}: không quay hôm nay ({now.strftime('%A')})")
            continue

        # Tránh gửi trùng trong ngày
        if state.get(game_id, {}).get("last_date") == today_str:
            print(f"[SKIP] {cfg['name']}: đã xử lý hôm nay")
            continue

        # Lấy kết quả hôm nay
        result_rec = get_latest_result(game_id)
        if not result_rec:
            print(f"[WAIT] {cfg['name']}: chưa có kết quả hôm nay")
            continue

        print(f"[OK] {cfg['name']}: {result_rec['result']}")
        section = build_game_section(game_id, result_rec, state)
        sections.append(section)

    if not sections:
        print("[INFO] Không có kết quả mới để gửi lần này.")
        return

    # Tổng điểm
    total_u = sum(state[g]["user_pts"] for g in GAMES)
    total_a = sum(state[g]["ai_pts"]   for g in GAMES)
    diff = total_u - total_a
    if diff > 0:
        lead_str = f"👤 Bạn dẫn <b>+{diff}đ</b> ⚠️ (AI sắp bị xóa!)"
    elif diff < 0:
        lead_str = f"🤖 AI dẫn <b>+{abs(diff)}đ</b>"
    else:
        lead_str = "Đang hòa 0đ"

    msg = "\n".join([
        f"🎰 <b>BOT XỔ SỐ VIETLOTT</b>",
        f"📅 {vn_weekday_str(now)} — {now.strftime('%H:%M')}",
        "━━━━━━━━━━━━━━━━━━━━",
        *sections,
        "\n━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>TỔNG ĐIỂM TÍCH LŨY</b>",
        f"👤 Bạn: <b>{total_u}đ</b>   🤖 AI: <b>{total_a}đ</b>",
        lead_str,
        f"\n⏰ Quét tiếp: {(now + datetime.timedelta(hours=1)).strftime('%H:%M')} {now.strftime('%d/%m/%Y')}",
    ])

    save_state(state)
    send_telegram(msg)

if __name__ == "__main__":
    main()
