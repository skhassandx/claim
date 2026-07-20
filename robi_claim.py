import requests
import json

def claim_daily_points():
    # API Endpoint
    url = "https://myrobi-prod.robi.com.bd/loyalty/loyalty/api/v1/earn-coins"

    # Request Headers
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0aWQiOiJkOTIxYTA2NS1lY2M3LTQ2YzAtOTU3ZS05MTA5OTY3YTAzOTAiLCJzdWIiOiIyNTI5NzgxMCIsImlsayI6Iis4ODAxODE4ODk2MTY2IiwicGF5dHlwZSI6InByZXBhaWQiLCJ0eXBlIjoiYWNjZXNzIiwiaXNzIjoicm9iaSIsImF1ZCI6Imh0dHA6Ly9sb2NhbGhvc3Q6MzAwMCIsInBsdCI6ImFuZHJvaWQiLCJ2ZXIiOiIxMC4xMi43IiwiZW52IjoiZGV2ZWxvcG1lbnQiLCJ1c2VyVHlwZSI6ImJyYW5kIiwibWFya2V0U2VnbWVudCI6ImluZGl2aWR1YWwiLCJjcmVhdGVkQXQiOjE1ODE5NTQwNzEsImlzRW1wbG95ZWUiOmZhbHNlLCJtYWluUHJvZHVjdCI6MjYwLCJzaW1UeXBlIjoibm9ybWFsIiwiaWF0IjoxNzg0NTI0ODkyLCJleHAiOjE3ODQ2MTEyOTJ9.8bgHBpHPXUp__UmHpAcmAglsGBpfWdtWdDidlZDHIP8",
        "Accept-Encoding": "gzip",
        "User-Agent": "Robi/10.12.7/android/30/4g/fa5ad50d15f996fc/WALTON_Primo H10/e6c3e076dbf731536666add7f9a418da",
        "Accept-Language": "bn",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive"
    }

    # Request Payload/Body
    payload = "type=daily-check-in"

    print("🚀 Sending request to claim Robi daily points...")
    
    try:
        # Sending the POST request
        response = requests.post(url, headers=headers, data=payload)
        
        # Checking if request was successful
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "success":
                coins = response_data.get("data", {}).get("coinsEarned", 0)
                print(f"✅ Success! You have earned {coins} coins.")
            else:
                print("⚠️ Request succeeded, but unexpected response format.")
                print(response.text)
        else:
            print(f"❌ Failed! Server returned Status Code: {response.status_code}")
            print(f"Error Details: {response.text}")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    claim_daily_points()
