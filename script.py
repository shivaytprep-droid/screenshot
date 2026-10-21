import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("वेबसाइट ओपन हो रही है...")
        try:
            page.goto('https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php', timeout=60000)
            
            print("लॉगिन डिटेल्स डाल रहे हैं...")
            page.locator('input[type="text"]').first.fill('sserjk')
            page.locator('input[type="password"]').first.fill('sserjk')
            page.keyboard.press('Enter')
            
            page.wait_for_timeout(10000) 
            
            for i in range(1, 3):
                file_name = f'dashboard_screenshot_{int(time.time())}.png'
                page.screenshot(path=file_name)
                print(f"स्क्रीनशॉट लिया गया: {file_name}")
                
                if i == 1:
                    print("2 मिनट का इंतज़ार कर रहे हैं...")
                    time.sleep(120)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    run()
