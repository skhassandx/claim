import requests
import json
import os

TOKEN_FILE = "tokens.json"

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def save_tokens(access_token, refresh_token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"accessToken": access_token, "refreshToken": refresh_token}, f, indent=4)
    print("💾 Tokens saved successfully.")

def get_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/4g/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "en",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive"
    }

def refresh_access_token(refresh_token):
    print("\n🔄 Access Token expired. Attempting to generate a new one...")
    
    # NOTE: This is the standard predicted endpoint for Robi refresh token.
    url = "https://myrobi-prod.robi.com.bd/api/v1/customer/auth/refresh"
    
    headers = {
        "User-Agent": "Robi/10.12.7/android/30/4g/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "en",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({"refreshToken": refresh_token})
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code in [200, 201]:
            data = response.json()
            new_access = data.get("data", {}).get("token", {}).get("accessToken")
            new_refresh = data.get("data", {}).get("token", {}).get("refreshToken", refresh_token)
            
            if new_access:
                print("✅ Token refreshed successfully!")
                save_tokens(new_access, new_refresh)
                return new_access
        
        print(f"❌ Token refresh failed. Status: {response.status_code}")
        print("⚠️ Note: The exact Refresh API endpoint might be different. You may need to capture the exact URL.")
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
    return None

def get_total_points(access_token, refresh_token):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/loyalty-and-coin"
    headers = get_headers(access_token)
    
    print("\n🔍 Fetching total points balance...")
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("📊 Current Balance Details:")
            print(json.dumps(data, indent=2))
            
        elif response.status_code == 401:
            new_token = refresh_access_token(refresh_token)
            if new_token:
                get_total_points(new_token, refresh_token) # Retry with new token
        else:
            print(f"❌ Failed to fetch balance. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def claim_daily_points(access_token, refresh_token):
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"
    headers = get_headers(access_token)
    payload = "type=daily-check-in"

    print("🚀 Sending request to claim daily points...")
    try:
        response = requests.post(url, headers=headers, data=payload)
        
        try:
            response_data = response.json()
        except:
            response_data = {}

        if response.status_code == 200 and response_data.get("status") == "success":
            coins = response_data.get("data", {}).get("coinsEarned", 0)
            print(f"✅ Success! You have earned {coins} points today.")
            return True
            
        elif response.status_code == 400:
            error_msg = response_data.get("error", {}).get("error", "Already claimed today.")
            print(f"⚠️ Notice: {error_msg}")
            return True
            
        elif response.status_code == 401:
            new_token = refresh_access_token(refresh_token)
            if new_token:
                return claim_daily_points(new_token, refresh_token) # Retry with new token
            return False
            
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    tokens = load_tokens()
    
    if not tokens or "accessToken" not in tokens:
        print("❌ tokens.json file not found or invalid! Please create it.")
    else:
        access_token = tokens["accessToken"]
        refresh_token = tokens["refreshToken"]
        
        claim_daily_points(access_token, refresh_token)
        print("-" * 40)
        get_total_points(access_token, refresh_token)
