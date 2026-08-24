import requests
import json
import os
import time
import random
import logging
import smtplib
from email.mime.text import MIMEText

TOKEN_FILE = "tokens.json"
MIN_DELAY_SECONDS = 5   # অ্যাকাউন্টগুলোর মাঝে ন্যূনতম গ্যাপ
MAX_DELAY_SECONDS = 60  # নেটওয়ার্ক স্পিড ভ্যারিয়েশন ও Robi সার্ভারের rate-limit এড়াতে সর্বোচ্চ গ্যাপ

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ইমেইল রিপোর্টের জন্য সব লগ লাইন এখানে জমা হবে
log_lines = []


def log(level, message):
    """একইসাথে logger-এ প্রিন্ট করে এবং ইমেইল রিপোর্টের জন্য জমা রাখে।"""
    getattr(logger, level)(message)
    log_lines.append(message)


def send_email_notification(subject, body):
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    email_to = os.environ.get("EMAIL_TO", email_user)  # EMAIL_TO না থাকলে নিজেকেই পাঠাবে

    if not email_user or not email_pass:
        logger.warning("EMAIL_USER / EMAIL_PASS সেট করা নেই। ইমেইল নোটিফিকেশন স্কিপ করা হলো।")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_to

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.sendmail(email_user, [email_to], msg.as_string())
        logger.info(f"ইমেইল সফলভাবে পাঠানো হয়েছে: {email_to}")
    except Exception as e:
        logger.error(f"ইমেইল পাঠাতে ব্যর্থ: {e}")


def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return []


def save_tokens(accounts):
    with open(TOKEN_FILE, "w") as f:
        json.dump(accounts, f, indent=4)
    log("info", "tokens.json ফাইল আপডেট করা হয়েছে।")


def get_headers(access_token=None, is_urlencoded=False):
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/WIFI/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "en",
        "Connection": "Keep-Alive",
    }

    if is_urlencoded:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        headers["Content-Type"] = "application/json; charset=utf-8"

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    return headers


def refresh_access_token(account):
    phone = account.get("phone", "Unknown")
    log("info", f"[{phone}] Access token রিফ্রেশ করার চেষ্টা করা হচ্ছে...")
    url = "https://myrobi-prod.robi.com.bd/api/v1/customer/auth/refresh"

    headers = get_headers(access_token=None)
    payload = json.dumps({"refresh_token": account.get("refreshToken", "").strip()})

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        if response.status_code in (200, 201):
            data = response.json()
            token_data = data.get("data", {}).get("token", {})
            new_access = token_data.get("accessToken")
            new_refresh = token_data.get("refreshToken", account.get("refreshToken"))
            if new_access:
                log("info", f"[{phone}] Token রিফ্রেশ সফল হয়েছে।")
                account["accessToken"] = new_access
                account["refreshToken"] = new_refresh
                return True
        log("error", f"[{phone}] Token রিফ্রেশ ব্যর্থ। Status: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Token রিফ্রেশ করার সময় নেটওয়ার্ক এরর: {e}")
    except Exception as e:
        log("error", f"[{phone}] Token রিফ্রেশ করার সময় অপ্রত্যাশিত এরর: {e}")
    return False


def get_total_points(account):
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/loyalty-and-coin"
    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]), timeout=15)
        if response.status_code == 200:
            data = response.json()
            inner = data.get("data", {})

            total_points = inner.get("totalPoints", "Unknown")
            tier = inner.get("loyaltyCategoryTitle", "Unknown")
            points_today = inner.get("pointsEarnedToday", 0)
            tier_expiry = inner.get("expiry", "Unknown")
            points_expiry = inner.get("nearestExpirationTime", "Unknown")
            points_expiring_soon = inner.get("nearestExpirationPointSum", 0)

            log("info", f"[{phone}] বর্তমান ব্যালেন্স: {total_points} Points")
            log("info", f"[{phone}] Tier: {tier}")
            log("info", f"[{phone}] Points Earned Today: {points_today}")
            log("info", f"[{phone}] Tier Validity: {tier_expiry}")
            log("info", f"[{phone}] Next Points Expiry: {points_expiring_soon} points on {points_expiry}")
            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Balance check-এ 401 (unauthorized)। Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] ব্যালেন্স আনতে ব্যর্থ। Status: {response.status_code}")
    except requests.RequestException as e:
        log("error", f"[{phone}] নেটওয়ার্ক এরর: {e}")
    return False, False


def claim_daily_points(account):
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"

    payload = "type=daily-check-in"
    headers = get_headers(account["accessToken"], is_urlencoded=True)

    log("info", f"[{phone}] ডেইলি পয়েন্ট ক্লেইমের রিকোয়েস্ট পাঠানো হচ্ছে...")
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response_data = response.json() if response.text else {}

        if response.status_code in (200, 201) and response_data.get("status") == "success":
            coins = response_data.get("data", {}).get("coinsEarned", 0)
            log("info", f"[{phone}] সফল! আজকে {coins} পয়েন্ট পাওয়া গেছে।")
            return True, False
        elif response.status_code == 400:
            error_msg = response_data.get("error", {}).get("error", "আজকে ইতিমধ্যে ক্লেইম করা হয়েছে।")
            log("warning", f"[{phone}] নোটিস: {error_msg}")
            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Claim-এ 401 (unauthorized)। Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] ব্যর্থ! Status Code: {response.status_code}")
    except requests.RequestException as e:
        log("error", f"[{phone}] নেটওয়ার্ক এরর: {e}")
    return False, False


def check_main_balance(account):
    """
    Diagnostic ফাংশন: main balance endpoint-এর পুরো raw response দেখায়,
    যাতে সঠিক field names (mainBalance, dataVolume ইত্যাদি) শনাক্ত করা যায়।
    ফিল্ড নাম কনফার্ম হওয়ার পর এটাকে ক্লিন আউটপুটে রূপান্তর করা হবে।
    """
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/account/api/v1/balance"

    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]), timeout=15)
        if response.status_code == 200:
            try:
                data = response.json()
                pretty = json.dumps(data, indent=2, ensure_ascii=False)
            except ValueError:
                pretty = response.text
            log("info", f"[{phone}] Main Balance RAW RESPONSE:\n{pretty}")
            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Main balance-এ 401 (unauthorized)। Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] Main balance আনতে ব্যর্থ। Status: {response.status_code} - {response.text[:200]}")
    except requests.RequestException as e:
        log("error", f"[{phone}] নেটওয়ার্ক এরর: {e}")
    return False, False


def process_account(account):
    """একটা অ্যাকাউন্টের জন্য claim + balance check, দরকার হলে token refresh সহ।"""
    phone = account.get("phone", "Unknown")
    token_refreshed = False

    success, needs_refresh = claim_daily_points(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)  # refresh-এর পর সাথে সাথে না পাঠিয়ে সামান্য গ্যাপ
            success, needs_refresh = claim_daily_points(account)
            if needs_refresh:
                log("error", f"[{phone}] Token রিফ্রেশের পরও claim-এ 401 — আরও গভীর সমস্যা থাকতে পারে (token blacklist/account issue), তদন্ত দরকার।")
        else:
            log("error", f"[{phone}] Token রিফ্রেশ ব্যর্থ হয়েছে। এই অ্যাকাউন্ট স্কিপ করা হলো।")
            return token_refreshed  # refresh ব্যর্থ হলে এই অ্যাকাউন্টের বাকি কাজ স্কিপ

    time.sleep(2)  # claim ও balance check-এর মাঝে সামান্য গ্যাপ

    success, needs_refresh = get_total_points(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)
            success, needs_refresh = get_total_points(account)
            if needs_refresh:
                log("error", f"[{phone}] Token রিফ্রেশের পরও balance check-এ 401 — আরও গভীর সমস্যা থাকতে পারে (token blacklist/account issue), তদন্ত দরকার।")

    time.sleep(2)  # main balance check-এর আগে সামান্য গ্যাপ

    success, needs_refresh = check_main_balance(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)
            check_main_balance(account)

    return token_refreshed


def main():
    accounts = load_tokens()
    if not accounts or not isinstance(accounts, list):
        log("error", "tokens.json ফাইলটি খালি অথবা সঠিক ফরম্যাটে নেই।")
        send_email_notification("Robi Claim - Failed", "\n".join(log_lines))
        return

    tokens_updated_globally = False

    for index, account in enumerate(accounts):
        phone = account.get("phone", f"Account {index + 1}")
        log("info", f"\n{'=' * 40}\nনাম্বার প্রসেস করা হচ্ছে: {phone}\n{'=' * 40}")

        if index > 0:
            delay_seconds = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            log("info", f"Rate-Limit Safety Delay: পরবর্তী অ্যাকাউন্টে যাওয়ার আগে {delay_seconds} সেকেন্ড অপেক্ষা করা হচ্ছে...")
            time.sleep(delay_seconds)

        if process_account(account):
            tokens_updated_globally = True

    if tokens_updated_globally:
        log("info", "নতুন token সহ tokens.json আপডেট করা হচ্ছে...")
        save_tokens(accounts)

    # ফাইনাল রিপোর্ট ইমেইলে পাঠানো
    send_email_notification("Robi Daily Point Claim - Report", "\n".join(log_lines))


if __name__ == "__main__":
    main()
