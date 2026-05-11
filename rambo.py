import requests
import re
import time
import asyncio
from telegram import Bot
from datetime import datetime
import hashlib

#---------------- TELEGRAM ----------------
TELEGRAM_TOKEN = "8540890334:AAF-GZOegnn5RloTvEuOKi4314JKDkwn72g"
CHAT_ID = "-1003688403205"

#---------------- IMS LOGIN ---------------
LOGIN_URL = "https://imssms.org/login"
SIGNIN_URL = "https://imssms.org/signin"
AJAX_URL = "https://imssms.org/client/res/data_smscdr.php"

USERNAME = "V39MohammedTar"
PASSWORD = "V39MohammedTar"

session = requests.Session()
session.verify = True  # تحقق SSL

# هيدرات للـ GET /login
LOGIN_GET_HEADERS = {
    "Host": "imssms.org",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-RO,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
}

# هيدرات للـ POST /signin
LOGIN_POST_HEADERS = {
    "Host": "imssms.org",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Origin": "https://imssms.org",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "Referer": "https://imssms.org/login",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-RO,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded",
}

# الهيدر العام للـ AJAX
AJAX_BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# لتخزين الرسائل المرسلة مسبقاً
sent_sms_cache = set()

def mask_number(number: str) -> str:
    digits = re.sub(r"\D", "", number)

    if len(digits) < 9:
        return number

    country = digits[:3]
    first = digits[3:6]
    last = digits[-3:]

    return f"+{country} {first} SMS {last}"

# ------------ استخراج OTP بشكل قوي ------------- #
def extract_otp(message: str) -> str:
    """
    يحاول يطلع أقوى كود ممكن من الرسالة:
    - أولاً كود مثل 123-456
    - بعدها أرقام 4-8
    - بعدها كلمات حروف+أرقام مثل 4sgLq1p5sV6
    """
    if not message:
        return "N/A"

    # 1) نمط 123-456
    m = re.search(r"\b(\d{3}-\d{3})\b", message)
    if m:
        return m.group(1)

    # 2) أرقام 4–8 (مع تجاهل أشياء مثل 249… الطويلة)
    candidates = re.findall(r"\b(\d{4,8})\b", message)
    if candidates:
        for c in candidates:
            if not c.startswith("249"):
                return c
        return candidates[0]

    # 3) حروف وأرقام 6–12 (مثل 4sgLq1p5sV6)
    m = re.search(r"\b([A-Za-z0-9]{6,12})\b", message)
    if m:
        return m.group(1)

    return "N/A"


def format_sms(row):
    time_sent = str(row[1])
    raw_number = str(row[2])
    service = str(row[3])
    message = str(row[4] or "").strip()

    otp = extract_otp(message)
    masked_number = mask_number(raw_number)

    text = (
        "🎯 *NEW CODE RECEIVED!*\n\n"
        f"🔑 *OTP* : `{otp}`\n\n"
        f"⚙️ *Service* : {service}\n"
        f"📱 *Number*  : {masked_number}\n"
        f"⏰ *Time*    : {time_sent}\n\n"
        "📄 *Full Message*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "```\n"
        f"{message}\n"
        "```\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 *Active & Ready*"
    )

    return text


def login():
    """تسجيل الدخول إلى الموقع"""
    print(f"[LOGIN] Loading login page at {datetime.now().strftime('%H:%M:%S')}...")

    try:
        # GET /login
        r = session.get(LOGIN_URL, headers=LOGIN_GET_HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"[LOGIN] FAILED, Status: {r.status_code}")
            return False

        # استخراج etkk
        etkk = re.search(r"name='etkk' value='(.*?)'", r.text)
        if not etkk:
            print("[ERROR] Cannot find etkk!")
            return False
        etkk = etkk.group(1)
        print(f"[ETKK] {etkk}")

        # استخراج captcha
        cap = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if not cap:
            print("[ERROR] Cannot find captcha!")
            return False

        c1, c2 = cap.groups()
        solved = int(c1) + int(c2)
        print(f"[CAPTCHA] {c1} + {c2} = {solved}")

        payload = {
            "etkk": etkk,
            "username": USERNAME,
            "password": PASSWORD,
            "capt": solved
        }

        # POST /signin
        p = session.post(
            SIGNIN_URL,
            headers=LOGIN_POST_HEADERS,
            data=payload,
            allow_redirects=True,
            timeout=10,
        )
        print(f"[LOGIN] Status: {p.status_code}")

        # التحقق من نجاح تسجيل الدخول
        if "SMSDashboard" in p.text or (p.url and ("SMSDashboard" in str(p.url) or "dashboard" in str(p.url))):
            print("[LOGIN] SUCCESS ✓")
            return True

        # محاولة التحقق بشكل آخر
        test_url = "https://imssms.org/client/SMSCDRStats"
        test_r = session.get(test_url, headers=LOGIN_GET_HEADERS, timeout=10)
        if test_r.status_code == 200 and "SMSCDRStats" in test_r.text:
            print("[LOGIN] SUCCESS (verified via dashboard) ✓")
            return True

        print("[LOGIN] FAILED ✗")
        return False

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return False


def fetch_latest_sms():
    """جلب أحدث الرسائل"""
    ts = int(time.time() * 1000)
    today = time.strftime("%Y-%m-%d")

    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "iDisplayStart": 0,
        "iDisplayLength": 5000,
        "sEcho": 1,
        "_": ts
    }

    ajax_headers = AJAX_BASE_HEADERS.copy()
    ajax_headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://imssms.org/client/SMSCDRStats"
    })

    try:
        r = session.get(AJAX_URL, headers=ajax_headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[ERROR] API returned status {r.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch SMS: {e}")
        return None


async def send_telegram_message(bot, chat_id, message):
    """إرسال رسالة إلى Telegram"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")
        return False


def create_sms_fingerprint(sms_data):
    """إنشاء بصمة فريدة لكل رسالة باستخدام كل البيانات"""
    fingerprint_str = f"{sms_data[0]}_{sms_data[1]}_{sms_data[2]}_{sms_data[4]}"
    return hashlib.md5(fingerprint_str.encode()).hexdigest()


async def main():
    """الدالة الرئيسية"""
    print("[SYSTEM] Starting SMS Monitor...")

    max_retries = 1
    for attempt in range(max_retries):
        if login():
            break
        if attempt < max_retries - 1:
            print(f"[RETRY] Login attempt {attempt + 1} failed, retrying in 5 seconds...")
            time.sleep(5)
        else:
            print("[FATAL] Login failed after multiple attempts.")
            return

    print("[SYSTEM] Logged in successfully.")
    print("[SYSTEM] Starting SMS monitoring...")

    bot = Bot(token=TELEGRAM_TOKEN)

    total_sms = 0
    last_check = datetime.now()
    initialized = False

    while True:
        try:
            print(f"\n[CHECK] Fetching SMS at {datetime.now().strftime('%H:%M:%S')}...")
            data = fetch_latest_sms()

            if not data:
                print("[WARN] No data returned, will retry...")
                time.sleep(3)
                continue

            rows = data.get("aaData", [])
            if not rows:
                print("[INFO] No SMS found in the response.")
                time.sleep(2)
                continue

            print(f"[INFO] Found {len(rows)} SMS in the response.")

            # أول تشغيل: نخزن الرسائل القديمة فقط بدون إرسال
            if not initialized:
                for row in rows:
                    if not row or len(row) < 5:
                        continue
                    msg = str(row[4] or "").strip()
                    number = str(row[2] or "").strip()
                    if not msg or msg == "0" or not number or number == "0":
                        continue
                    fp = create_sms_fingerprint(row)
                    sent_sms_cache.add(fp)
                initialized = True
                print("[INIT] Cache primed with existing SMS. Waiting for new messages...")
                time.sleep(2)
                continue

            # معالجة الرسائل من الأقدم للأحدث
            for row in reversed(rows):
                if not row or len(row) < 5:
                    continue

                msg = str(row[4] or "").strip()
                number = str(row[2] or "").strip()

                if not msg or msg == "0":
                    continue
                if not number or number == "0":
                    continue

                sms_fingerprint = create_sms_fingerprint(row)

                if sms_fingerprint not in sent_sms_cache:
                    formatted_msg = format_sms(row)

                    success = await send_telegram_message(bot, CHAT_ID, formatted_msg)
                    if success:
                        sent_sms_cache.add(sms_fingerprint)
                        total_sms += 1
                        print(f"[NEW SMS] Sent SMS ID: {row[0]} | Total sent: {total_sms}")
                    else:
                        print(f"[ERROR] Failed to send SMS ID: {row[0]}")

            if len(sent_sms_cache) > 1000:
                sent_sms_cache.clear()
                print("[CACHE] Cache cleared to avoid memory issues.")

            if (datetime.now() - last_check).seconds > 60:
                print(f"[STATS] Total SMS sent: {total_sms} | Cache size: {len(sent_sms_cache)}")
                last_check = datetime.now()

            time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n[SYSTEM] Stopped by user | Total SMS processed: {total_sms}")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            print("[RECONNECT] Attempting to reconnect...")
            if not login():
                print("[ERROR] Reconnection failed, waiting 10 seconds before retry...")
            time.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Program terminated by user")

