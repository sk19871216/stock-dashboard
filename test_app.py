from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("正在访问 Streamlit 应用...")
    page.goto('http://localhost:8501')
    page.wait_for_load_state('networkidle')
    
    print("页面加载完成，正在截图...")
    page.screenshot(path='f:/trae_project/股票看板/test_screenshot.png', full_page=True)
    
    title = page.title()
    print(f"页面标题: {title}")
    
    print("\n检查页面内容...")
    content = page.content()
    if "股票数据看板" in content:
        print("✅ 找到股票数据看板标题")
    else:
        print("⚠️ 未找到标题")
    
    if "数据更新" in content:
        print("✅ 找到数据更新功能")
    else:
        print("⚠️ 未找到数据更新功能")
    
    if "情报追踪" in content:
        print("✅ 找到情报追踪功能")
    else:
        print("⚠️ 未找到情报追踪功能")
    
    print("\n检查控制台日志...")
    page.on('console', lambda msg: print(f"Console {msg.type}: {msg.text}"))
    
    browser.close()
    print("\n测试完成！")
