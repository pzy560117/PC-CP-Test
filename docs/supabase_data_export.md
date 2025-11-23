# Supabase 数据导出工具文档

## 功能说明

从 Supabase 数据库读取全部数据并导出到本地文件（支持 JSON、CSV、Excel 格式）。

## 环境要求

```bash
pip install requests pandas openpyxl
```

## 配置说明

### 1. Supabase 配置参数

```python
SUPABASE_CONFIG = {
    "rest_url": "https://your-project.supabase.co/rest/v1",
    "api_key": "your-anon-or-service-key",
    "table": "recommendations",  # 要读取的表名
    "timeout": 30
}
```
  "supabase": {
    "enabled": true,
    "rest_url": "https://uspeqkgnmkwmqnctytxu.supabase.co/rest/v1",
    "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVzcGVxa2dubWt3bXFuY3R5dHh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4NTExNzAsImV4cCI6MjA3OTQyNzE3MH0.yFu4dghvEP_jRpiL7JisO5vDaqXMkSuTnRw8oeBrZ4s",
    "table": "recommendations",
    "timeout": 10
  },
### 2. 获取 Supabase 凭证

- **REST URL**: 项目设置 → API → Project URL
- **API Key**: 项目设置 → API → anon public key 或 service_role key
- **表名**: 数据库中的表名称

## 核心实现

### 1. 从 Supabase 读取全部数据

```python
import requests
from typing import List, Dict, Optional

def fetch_all_data(
    rest_url: str,
    api_key: str,
    table: str,
    timeout: int = 30,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """
    从 Supabase 读取全部数据
    
    Args:
        rest_url: Supabase REST API 地址
        api_key: API 密钥
        table: 表名
        timeout: 请求超时时间
        filters: 可选过滤条件，例如 {"status": "eq.pending"}
    
    Returns:
        数据列表
    """
    endpoint = f"{rest_url}/{table}"
    
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
    }
    
    # 构建查询参数
    params = {"select": "*"}  # 查询所有字段
    if filters:
        params.update(filters)
    
    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        print(f"成功获取 {len(data)} 条记录")
        return data
    except Exception as e:
        print(f"读取数据失败: {e}")
        return []
```

### 2. 分页读取大数据集

```python
def fetch_all_data_with_pagination(
    rest_url: str,
    api_key: str,
    table: str,
    page_size: int = 1000
) -> List[Dict]:
    """
    分页读取大量数据
    
    Args:
        page_size: 每页数据量
    """
    endpoint = f"{rest_url}/{table}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Range-Unit": "items",
    }
    
    all_data = []
    offset = 0
    
    while True:
        # Supabase 使用 Range 头进行分页
        headers["Range"] = f"{offset}-{offset + page_size - 1}"
        
        response = requests.get(endpoint, headers=headers, params={"select": "*"})
        response.raise_for_status()
        
        data = response.json()
        if not data:
            break
        
        all_data.extend(data)
        print(f"已获取 {len(all_data)} 条记录...")
        
        if len(data) < page_size:
            break
        
        offset += page_size
    
    return all_data
```

### 3. 导出到文件

#### 导出为 JSON

```python
import json
from datetime import datetime

def export_to_json(data: List[Dict], output_path: str = None):
    """导出为 JSON 文件"""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"supabase_export_{timestamp}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已导出到: {output_path}")
    return output_path
```

#### 导出为 CSV

```python
import pandas as pd

def export_to_csv(data: List[Dict], output_path: str = None):
    """导出为 CSV 文件"""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"supabase_export_{timestamp}.csv"
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"已导出到: {output_path}")
    return output_path
```

#### 导出为 Excel

```python
def export_to_excel(data: List[Dict], output_path: str = None):
    """导出为 Excel 文件"""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"supabase_export_{timestamp}.xlsx"
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False, engine="openpyxl")
    
    print(f"已导出到: {output_path}")
    return output_path
```

## 完整示例

### 基础导出脚本

```python
#!/usr/bin/env python3
"""Supabase 数据导出工具"""

import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict

# 配置
SUPABASE_CONFIG = {
    "rest_url": "https://uspeqkgnmkwmqnctytxu.supabase.co/rest/v1",
    "api_key": "your-api-key-here",
    "table": "recommendations",
}

def main():
    """主函数"""
    # 1. 读取数据
    print("开始读取 Supabase 数据...")
    data = fetch_all_data(
        rest_url=SUPABASE_CONFIG["rest_url"],
        api_key=SUPABASE_CONFIG["api_key"],
        table=SUPABASE_CONFIG["table"]
    )
    
    if not data:
        print("未获取到数据")
        return
    
    # 2. 导出为多种格式
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    export_to_json(data, f"output/data_{timestamp}.json")
    
    # CSV
    export_to_csv(data, f"output/data_{timestamp}.csv")
    
    # Excel
    export_to_excel(data, f"output/data_{timestamp}.xlsx")
    
    print(f"\n导出完成！共 {len(data)} 条记录")

if __name__ == "__main__":
    main()
```

## 高级用法

### 1. 带过滤条件的查询

```python
# 查询特定状态的记录
filters = {
    "status": "eq.pending",  # 状态等于 pending
    "order": "created_at.desc",  # 按创建时间降序
    "limit": "100"  # 限制数量
}

data = fetch_all_data(
    rest_url=rest_url,
    api_key=api_key,
    table="recommendations",
    filters=filters
)
```

### 2. 选择特定字段

```python
# 只查询特定字段
params = {
    "select": "id,period,recommended_numbers,created_at"
}

response = requests.get(
    f"{rest_url}/{table}",
    headers=headers,
    params=params
)
```

### 3. 复杂查询

```python
# 日期范围查询
filters = {
    "created_at": "gte.2025-01-01T00:00:00Z",  # 大于等于
    "created_at": "lt.2025-12-31T23:59:59Z",   # 小于
}

# 模糊查询
filters = {
    "period": "like.*202501*"  # 期号包含 202501
}

# 多条件组合
filters = {
    "and": "(status.eq.pending,order_index.gte.1)"
}
```

## 项目结构建议

```
supabase-export/
├── config/
│   └── config.json          # 配置文件
├── output/                  # 导出文件目录
├── src/
│   ├── fetcher.py          # 数据获取模块
│   ├── exporter.py         # 数据导出模块
│   └── utils.py            # 工具函数
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
└── README.md              # 项目说明
```

## 注意事项

1. **API 限流**: Supabase 免费版有请求频率限制，大数据量建议使用分页
2. **超时设置**: 大表查询建议增加 timeout 值
3. **API Key 安全**: 不要将 API Key 提交到版本控制系统
4. **数据类型**: JSON 字段需要手动解析（如 `recommended_numbers`）
5. **时区处理**: Supabase 存储 UTC 时间，导出时注意时区转换

## 完整依赖

```txt
requests==2.31.0
pandas==2.1.3
openpyxl==3.1.2
```

## 快速启动

1. 安装依赖：`pip install -r requirements.txt`
2. 修改配置：填入你的 Supabase 凭证
3. 运行脚本：`python main.py`
4. 查看导出：检查 `output/` 目录

## 相关资源

- [Supabase REST API 文档](https://supabase.com/docs/guides/api)
- [PostgREST 查询语法](https://postgrest.org/en/stable/api.html)
