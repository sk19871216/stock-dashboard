import requests
from bs4 import BeautifulSoup

try:
    print("正在测试 Streamlit 应用...")
    response = requests.get('http://localhost:8501', timeout=5)
    
    if response.status_code == 200:
        print(f"✅ 应用响应正常 (状态码: {response.status_code})")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title')
        if title:
            print(f"页面标题: {title.text}")
        
        if "股票" in response.text:
            print("✅ 页面包含股票相关内容")
        
        if "Streamlit" in response.text:
            print("✅ 确认为 Streamlit 应用")
        
        print("\n✅ 测试通过！应用已成功启动并运行！")
    else:
        print(f"❌ 应用返回异常状态码: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ 无法连接到应用，请检查应用是否正在运行")
except Exception as e:
    print(f"❌ 测试失败: {e}")
