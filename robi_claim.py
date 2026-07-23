import requests
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

TOKEN_FILE = "tokens.json"

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(accounts):
    with open(TOKEN_FILE, "w") as f:
        json.dump(accounts, f, indent=4)
    print("💾 tokens.json file auto-updated successfully.")

def get_headers(access_token=None):
    # আপনার দেওয়া অরিজিনাল হেডারগুলোর হুবহু ব্যবহার
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/WIFI/b9a78a8dc8ccac9c/WALTON_Primo H10/c15a12e8e7cbd416cf0264139b9e88e3",
        "Accept-Language": "en",
        "Content-Type": "application/json; charset=UTF-8",
        "Host": "myrobi-prod.robi.com.bd",
        "Connection": "Keep-Alive"
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers

def refresh_access_token(account):
    url = "https://myrobi-prod.robi.com.bd/api/v1/customer/auth/refresh"
    headers = get_headers()
    # রিফ্রেশের জন্য Authorization হেডারে পুরনো Refresh Token পাঠাতে হবে
    headers["Authorization"] = f"Bearer {account.get('refreshToken')}"
    
    payload = json.dumps({"refreshToken": account.get("refreshToken")})
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code in [200, 201]:
            data = response.json()
            new_access = data.get("data", {}).get("token", {}).get("accessToken")
            new_refresh = data.get("data", {}).get("token", {}).get("refreshToken", account.get("refreshToken"))
            
            if new_access:
                account["accessToken"] = new_access
                account["refreshToken"] = new_refresh
                print("✅ Token refreshed successfully! Memory updated.")
                return True
        else:
            print(f"⚠️ Refresh Failed! Server response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Critical error during token refresh: {e}")
        
    return False

def get_total_points(account):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/loyalty-and-coin"
    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]))
        if response.status_code == 200:
            return response.json().get("data", {}).get("totalPoints", "Unknown"), False
        elif response.status_code == 401:
            return None, True
    except Exception as e:
        pass
    return "Error", False

def claim_daily_points(account):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"
    payload = json.dumps({"type": "daily-check-in"})
    try:
        response = requests.post(url, headers=get_headers(account["accessToken"]), data=payload)
        response_data = response.json() if response.text else {}
        
        if response.status_code in [200, 201] and response_data.get("status") == "success":
            return response_data.get("data", {}).get("coinsEarned", 0), "Success", False
        elif response.status_code == 400:
            return 0, "Already Claimed", False
        elif response.status_code == 401:
            return 0, "Failed", True
    except Exception as e:
        return 0, f"Error: {e}", False
    return 0, f"Failed ({response.status_code})", False

def send_email_report(summary_text):
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASS")
    receiver_email = "hassanalmamundx00@gmail.com"

    if not sender_email or not sender_password:
        print("⚠️ Email credentials not found in GitHub Secrets. Skipping email.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "✅ Robi Auto Point Claim Report"
    msg.attach(MIMEText(summary_text, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("📧 Email report sent successfully to hassanalmamundx00@gmail.com!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def main():
    accounts = load_tokens()
    if not accounts:
        print("❌ tokens.json is empty!")
        return

    tokens_updated = False
    email_summary = "Robi Daily Points Execution Report:\n\n"

    for index, account in enumerate(accounts):
        phone = account.get("phone", f"Account {index+1}")
        print(f"\n📱 Processing Number: {phone}")
        
        # 1. Point Claim Process
        earned, msg, needs_refresh = claim_daily_points(account)
        if needs_refresh:
            print("🔄 Access Token expired. Attempting to refresh...")
            if refresh_access_token(account):
                tokens_updated = True
                earned, msg, _ = claim_daily_points(account)
            else:
                msg = "Token Refresh Failed"
                
        # 2. Total Balance Check
        total, needs_refresh = get_total_points(account)
        if needs_refresh:
            print("🔄 Access Token expired during balance check. Attempting to refresh...")
            if refresh_access_token(account):
                 tokens_updated = True
                 total, _ = get_total_points(account)
        
        report_line = f"[{phone}] - Earned: {earned} ({msg}) | Total Balance: {total} Points\n"
        print(report_line.strip())
        email_summary += report_line

    # 3. Save new tokens back to the JSON file if any refresh happened
    if tokens_updated:
        save_tokens(accounts)
        email_summary += "\n🔄 Note: Access tokens were successfully auto-refreshed today."

    send_email_report(email_summary)

if __name__ == "__main__":
    main()
