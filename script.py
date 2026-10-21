import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        try:
            # 1. Login page open karna
            page.goto('https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php', timeout=60000)
            
            # 2. Login karna
            page.locator('input[type="text"]').first.fill('sserjk')
            page.locator('input[type="password"]').first.fill('sserjk')
            page.keyboard.press('Enter')
            
            print("Login ho raha hai, home page aane ka wait kar rahe hain...")
            # Home page par poori tarah redirect hone ke liye 8 second ka wait
            page.wait_for_timeout(8000) 
            
            print("Ab wapas deviceListOnly page par ja rahe hain...")
            # 3. Home page se wapas deviceonly page par jana
            page.goto('https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php', timeout=60000)
            
            # Page ko theek se load hone ke liye 5 second ka time
            page.wait_for_timeout(5000) 
            
            # 4. Screenshot lena
            for i in range(1, 3):
                file_name = f'dashboard_screenshot_{int(time.time())}.png'
                page.screenshot(path=file_name, full_page=True)
                print(f"Screenshot liya gaya: {file_name}")
                
                if i == 1:
                    print("2 minute ruk rahe hain...")
                    time.sleep(120)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    run()
