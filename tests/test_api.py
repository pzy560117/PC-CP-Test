"""测试API返回内容"""
import pathlib
import requests

url = "https://kjapi.com/hall/hallhistory/txffcqiqu/ksffc"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    preview = response.text[:500]
    print(f"\n原始内容（前500字符）：")
    print(preview)

    # 保存到本地文件以便分析
    output_dir = pathlib.Path("temp")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "kjapi_response.html"
    output_file.write_text(response.text, encoding="utf-8")
    print(f"\n已将完整响应保存到: {output_file}")
    
    # 尝试解析JSON
    try:
        data = response.json()
        print(f"\n✓ JSON解析成功")
        print(f"数据结构: {type(data)}")
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
        elif isinstance(data, list) and len(data) > 0:
            print(f"列表长度: {len(data)}")
            print(f"第一项: {data[0]}")
    except Exception as e:
        print(f"\n✗ JSON解析失败: {e}")
        
except Exception as e:
    print(f"请求失败: {e}")
