import requests
import json

url = "https://crawler-api-7eco.onrender.com/crawl"
headers = {"Content-Type": "application/json"}
data = {"url": "https://captionocean.com"}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {str(e)}") 