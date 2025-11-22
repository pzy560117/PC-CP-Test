"""查看开奖详情页面"""
import pathlib
import requests

url = "https://kjapi.com/hallhistoryDetail/txffcqiqu/2025-11-23"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html",
}

resp = requests.get(url, headers=headers, timeout=10)
print(resp.status_code, resp.headers.get("Content-Type"))
html = resp.text
path = pathlib.Path("temp/detail.html")
path.write_text(html, encoding="utf-8")
print(f"saved to {path}")
