import requests
import json

def get_total_points(headers):
    # Endpoint for fetching total loyalty points/coins balance
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/loyalty-and-coin"
    
    print("\n🔍 Fetching total points balance...")
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Printing the JSON response properly formatted
            print("📊 Current Balance Details:")
            print(json.dumps(data, indent=2))
        elif response.status_code == 401:
            print("❌ Cannot fetch balance: JWT Token has expired.")
        else:
            print(f"❌ Failed to fetch balance. Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching balance: {e}")

def claim_daily_points():
    # Endpoint for claiming daily points
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"

    # Headers with English Language Preference
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0aWQiOiJkOTIxYTA2NS1lY2M3LTQ2YzAtOTU3ZS05MTA5OTY3YTAzOTAiLCJzdWIiOiIyNTI5NzgxMCIsImlsayI6Iis4ODAxODE4ODk2MTY2IiwicGF5dHlwZSI6InByZXBhaWQiLCJ0eXBlIjoiYWNjZXNzIiwiaXNzIjoicm9iaSIsImF1ZCI6Imh0dHA6Ly9sb2NhbGhvc3Q6MzAwMCIsInBsdCI6ImFuZHJvaWQiLCJ2ZXIiOiIxMC4xMi43IiwiZW52IjoiZGV2ZWxvcG1lbnQiLCJ1c2VyVHlwZSI6ImJyYW5kIiwibWFya2V0U2VnbWVudCI6ImluZGl2aWR1YWwiLCJjcmVhdGVkQXQiOjE1ODE5NTQwNzEsImlzRW1wbG95ZWUiOmZhbHNlLCJtYWluUHJvZHVjdCI6MjYwLCJzaW1UeXBlIjoibm9ybWFsIiwiaWF0IjoxNzg0NTI0ODkyLCJleHAiOjE3ODQ2MTEyOTJ9.8bgHBpHPXUp__UmHpAcmAglsGBpfWdtWdDidlZDHIP8",
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/4g/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "en", # Changed to 'en' for English server responses
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive"
    }

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
            
        elif response.status_code == 400:
            error_msg = response_data.get("error", {}).get("error", "Already claimed today or unknown error occurred.")
            print(f"⚠️ Notice: {error_msg}")
            
        elif response.status_code == 401:
            print("❌ Failed: Your JWT Token has expired! Please capture a new token and update the script.")
            return # Stop execution so it doesn't try to fetch balance with an expired token
            
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        
    print("-" * 40)
    
    # Trigger the function to show total points balance
    get_total_points(headers)

if __name__ == "__main__":
    claim_daily_points()
