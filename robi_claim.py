import requests
import json
import os
import time
import random

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

def get_headers(access_token=None, is_urlencoded=False):
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/WIFI/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "en",
        "Connection": "Keep-Alive"
    }
    
    if is_urlencoded:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        headers["Content-Type"] = "application/json; charset=utf-8"
        
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        
    return headers

def refresh_access_token(account):
    print(f"🔄 Access Token expired for {account.get('phone', 'Unknown')}. Attempting to refresh...")
    url = "https://myrobi-prod.robi.com.bd/api/v1/customer/auth/refresh"
    
    # রিফ্রেশ করার সময় Authorization হেডার যাবে না, শুধু সাধারণ হেডার যাবে
    headers = get_headers(access_token=None)
    
    # 🚨 ফিক্স: পেলোডে অবশ্যই "refresh_token" (আন্ডারস্কোর সহ) থাকতে হবে
    payload = json.dumps({"refresh_token": account.get("refreshToken", "").strip()})
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code in [200, 201]:
            data = response.json()
            new_access = data.get("data", {}).get("token", {}).get("accessToken")
            new_refresh = data.get("data", {}).get("token", {}).get("refreshToken", account.get("refreshToken"))
            if new_access:
                print("✅ Token refreshed successfully!")
                account["accessToken"] = new_access
                account["refreshToken"] = new_refresh
                return True
        else:
            print(f"❌ Token refresh failed. Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
    return False

def get_total_points(account):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/loyalty-and-coin"
    try:
        response = requests.get(url, headers=get_headers(account["accessToken"]))
        if response.status_code == 200:
            data = response.json()
            total_points = data.get("data", {}).get("totalPoints", "Unknown")
            print(f"📊 Current Balance: {total_points} Points")
            return True, False
        elif response.status_code == 401:
            return False, True
        else:
            print(f"❌ Failed to fetch balance. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False, False

def claim_daily_points(account):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"
    
    # 🚨 ফিক্স: পেলোড URL-encoded হতে হবে, JSON নয়
    payload = "type=daily-check-in"
    headers = get_headers(account["accessToken"], is_urlencoded=True)
    
    print("🚀 Sending request to claim daily points...")
    try:
        response = requests.post(url, headers=headers, data=payload)
        response_data = response.json() if response.text else {}
        
        if response.status_code in [200, 201] and response_data.get("status") == "success":
            coins = response_data.get("data", {}).get("coinsEarned", 0)
            print(f"✅ Success! Earned {coins} points today.")
            return True, False
        elif response.status_code == 400:
            error_msg = response_data.get("error", {}).get("error", "Already claimed today.")
            print(f"⚠️ Notice: {error_msg}")
            return True, False
        elif response.status_code == 401:
            return False, True
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    return False, False

def main():
    accounts = load_tokens()
    if not accounts or not isinstance(accounts, list):
        print("❌ tokens.json is empty or invalid.")
        return

    tokens_updated_globally = False

    for index, account in enumerate(accounts):
        phone = account.get("phone", f"Account {index+1}")
        print(f"\n{'='*40}\n📱 Processing Number: {phone}\n{'='*40}")
        
        # ⏳ 🚨 ফিক্স: অ্যান্টি-বট ডিলে ৫ থেকে ১৫ সেকেন্ড করা হলো (GitHub টাইমআউট এড়াতে)
        if index > 0:
            delay_seconds = random.randint(5, 60)
            print(f"⏳ Anti-Bot Delay: Waiting for {delay_seconds} seconds before processing next account...")
            time.sleep(delay_seconds)
        
        success, needs_refresh = claim_daily_points(account)
        if needs_refresh:
            if refresh_access_token(account):
                tokens_updated_globally = True
                claim_daily_points(account)
            else:
                continue
                
        success, needs_refresh = get_total_points(account)
        if needs_refresh:
             if refresh_access_token(account):
                 tokens_updated_globally = True
                 get_total_points(account)

    if tokens_updated_globally:
        print("\n🔄 Updating tokens.json with new keys...")
        save_tokens(accounts)

if __name__ == "__main__":
    main()
