import requests
import json
import os
import time
import random
import logging
import smtplib
from email.mime.text import MIMEText

TOKEN_FILE = "tokens.json"
MIN_DELAY_SECONDS = 5   
MAX_DELAY_SECONDS = 60  

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

log_lines = []

def log(level, message):
    """একইসাথে logger-এ প্রিন্ট করে এবং ইমেইল রিপোর্টের জন্য জমা রাখে।"""
    getattr(logger, level)(message)
    log_lines.append(message)


def send_email_notification(subject, body):
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    email_to = os.environ.get("EMAIL_TO", email_user)  

    if not email_user or not email_pass:
        logger.warning("EMAIL_USER / EMAIL_PASS not set. Skipping email notification.")
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
        logger.info(f"Email sent successfully to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return []


def save_tokens(accounts):
    with open(TOKEN_FILE, "w") as f:
        json.dump(accounts, f, indent=4)
    log("info", "tokens.json file updated successfully.")


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
    log("info", f"[{phone}] Attempting to refresh access token...")
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
                log("info", f"[{phone}] Token refreshed successfully!")
                account["accessToken"] = new_access
                account["refreshToken"] = new_refresh
                return True
        log("error", f"[{phone}] Token refresh failed. Status: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Network error while refreshing token: {e}")
    except Exception as e:
        log("error", f"[{phone}] Unexpected error while refreshing token: {e}")
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

            log("info", f"[{phone}] Current Balance: {total_points} Points")
            log("info", f"[{phone}] Tier: {tier}")
            log("info", f"[{phone}] Points Earned Today: {points_today}")
            log("info", f"[{phone}] Tier Validity: {tier_expiry}")
            log("info", f"[{phone}] Next Points Expiry: {points_expiring_soon} points on {points_expiry}")
            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Loyalty balance check got 401 (unauthorized). Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] Failed to fetch loyalty balance. Status: {response.status_code}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Network error: {e}")
    return False, False


def claim_daily_points(account):
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"

    payload = "type=daily-check-in"
    headers = get_headers(account["accessToken"], is_urlencoded=True)

    log("info", f"[{phone}] Sending request to claim daily points...")
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response_data = response.json() if response.text else {}

        if response.status_code in (200, 201) and response_data.get("status") == "success":
            coins = response_data.get("data", {}).get("coinsEarned", 0)
            log("info", f"[{phone}] Success! Earned {coins} points today.")
            return True, False
        elif response.status_code == 400:
            error_msg = response_data.get("error", {}).get("error", "Already claimed today.")
            log("warning", f"[{phone}] Notice: {error_msg}")
            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Claim request got 401 (unauthorized). Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] Failed! Status Code: {response.status_code}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Network error: {e}")
    return False, False


def check_main_balance(account):
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/account/api/v1/balance"

    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]), timeout=15)
        if response.status_code == 200:
            data = response.json().get("data", {})

            main = data.get("main", {})
            mb_data = data.get("data", {})
            voice = data.get("voice", {})

            main_balance = main.get("balance_str", "Unknown")
            main_unit = main.get("unit", "")
            main_expiry = main.get("translated_date") or "No expiry info"

            data_balance = mb_data.get("balance_str", "Unknown")
            data_unit = mb_data.get("unit", "MB")
            has_unlimited_data = mb_data.get("has_unlimited_data", False)
            data_expiry = mb_data.get("translated_date")

            voice_balance = voice.get("balance_str", "Unknown")
            voice_unit = voice.get("unit", "Min")
            voice_expiry = voice.get("translated_date")

            log("info", f"[{phone}] Main Balance: {main_unit}{main_balance} (Expiry: {main_expiry})")

            if main.get("is_expired"):
                log("warning", f"[{phone}] ⚠️ Main balance validity has expired!")

            alert = data.get("alert")
            if alert and alert.get("title"):
                log("warning", f"[{phone}] Alert: {alert.get('title')}")

            if has_unlimited_data:
                log("info", f"[{phone}] Internet: Unlimited")
            else:
                expiry_text = f" (Expiry: {data_expiry})" if data_expiry else " (No active package)"
                log("info", f"[{phone}] Internet: {data_balance} {data_unit}{expiry_text}")

            voice_expiry_text = f" (Expiry: {voice_expiry})" if voice_expiry else " (No active package)"
            log("info", f"[{phone}] Minutes: {voice_balance} {voice_unit}{voice_expiry_text}")

            loan = data.get("loan", {})
            outstanding_loan = loan.get("outstanding_loan")
            if outstanding_loan:
                log("info", f"[{phone}] Outstanding Loan: {outstanding_loan}")

            loan_alert = loan.get("alert")
            if loan_alert and loan_alert.get("title"):
                log("warning", f"[{phone}] Loan Alert: {loan_alert.get('title')}")

            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] Main balance check got 401 (unauthorized). Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] Failed to fetch main balance. Status: {response.status_code} - {response.text[:200]}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Network error: {e}")
    return False, False


def check_my_offers(account):
    phone = account.get("phone", "Unknown")
    url = "https://myrobi-prod.robi.com.bd/package/api/v1/packs-for-you"

    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]), timeout=15)
        if response.status_code == 200:
            data = response.json().get("data", {})
            suggested = data.get("suggestedForYou") or []
            additional = data.get("additionalOffers") or []
            offers = suggested + additional

            if not offers:
                log("info", f"[{phone}] My Offer: No package offers found right now.")
                return True, False

            log("info", f"[{phone}] My Offer: {len(offers)} package(s) available")
            for pack in offers:
                title = pack.get("title", "Unknown Package")
                price = pack.get("price", {}).get("total_price", "N/A")
                validity = pack.get("validity", {})
                validity_str = f"{validity.get('validity', '?')} {validity.get('validity_unit', '')}".strip()

                log("info", f"  - {title} | Price: Tk.{price} | Validity: {validity_str}")

            return True, False
        elif response.status_code == 401:
            log("warning", f"[{phone}] My Offer check got 401 (unauthorized). Response: {response.text[:200]}")
            return False, True
        else:
            log("error", f"[{phone}] Failed to fetch My Offer. Status: {response.status_code} - {response.text[:200]}")
    except requests.RequestException as e:
        log("error", f"[{phone}] Network error: {e}")
    return False, False


def probe_catalog_endpoints(account):
    phone = account.get("phone", "Unknown")
    candidate_paths = [
        "/package/api/v1/catalog",
        "/package/api/v1/all-packs",
        "/package/api/v1/packages",
        "/package/api/v1/package-list",
        "/package/api/v1/internet-packs",
        "/package/api/v1/data-packs",
        "/package/api/v1/categories",
    ]
    headers = get_headers(account["accessToken"])

    log("info", f"[{phone}] Probing possible catalog endpoints...")
    for path in candidate_paths:
        url = f"https://myrobi-prod.robi.com.bd{path}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            log("info", f"  GET {path} -> {response.status_code}")
            if response.status_code == 200:
                log("info", f"    Possible match! Response preview: {response.text[:300]}")
        except requests.RequestException as e:
            log("info", f"  GET {path} -> network error: {e}")


def process_account(account):
    """একটা অ্যাকাউন্টের জন্য claim + loyalty balance + main balance, দরকার হলে token refresh সহ।"""
    phone = account.get("phone", "Unknown")
    token_refreshed = False

    success, needs_refresh = claim_daily_points(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)  
            success, needs_refresh = claim_daily_points(account)
            if needs_refresh:
                log("error", f"[{phone}] Still getting 401 on claim after token refresh — deeper issue possible.")
        else:
            log("error", f"[{phone}] Token refresh failed. This account is being skipped.")
            return token_refreshed  

    time.sleep(2)  

    success, needs_refresh = get_total_points(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)
            success, needs_refresh = get_total_points(account)
            if needs_refresh:
                log("error", f"[{phone}] Still getting 401 on balance check after token refresh.")

    time.sleep(2)  

    success, needs_refresh = check_main_balance(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)
            check_main_balance(account)

    time.sleep(2)  

    success, needs_refresh = check_my_offers(account)
    if needs_refresh:
        if refresh_access_token(account):
            token_refreshed = True
            time.sleep(2)
            check_my_offers(account)

    return token_refreshed


def main():
    accounts = load_tokens()
    if not accounts or not isinstance(accounts, list):
        log("error", "tokens.json is empty or has an invalid format.")
        send_email_notification("Robi Claim - Failed", "\n".join(log_lines))
        return

    tokens_updated_globally = False

    for index, account in enumerate(accounts):
        phone = account.get("phone", f"Account {index + 1}")
        log("info", f"\n{'=' * 40}\nProcessing Number: {phone}\n{'=' * 40}")

        if index > 0:
            delay_seconds = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            log("info", f"Rate-Limit Safety Delay: waiting {delay_seconds} seconds before the next account...")
            time.sleep(delay_seconds)

        if process_account(account):
            tokens_updated_globally = True

    if tokens_updated_globally:
        log("info", "Updating tokens.json with new tokens...")
        save_tokens(accounts)

    send_email_notification("Robi Daily Point Claim - Report", "\n".join(log_lines))


if __name__ == "__main__":
    main()
