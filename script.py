import time
from playwright.sync_api import sync_playwright

def open_correct_page(page, target_url):
    print("Sahi page kholne ki koshish...")
    
    # Tarika 1: Menu bar me agar deviceListOnly ka direct link/button hai to uspar click karo
    link = page.locator("a[href*='dashboard_deviceListOnly.php']")
    if link.count() > 0:
        print("Menu me link mil gaya, click kar rahe hain...")
        link.first.click(force=True)
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)
    else:
        # Tarika 2: Agar menu me link chhupa hai, to Status par click karo ya JS se force open karo
        print("JavaScript se page force-open kar rahe hain...")
        page.evaluate(f"window.location.href = '{target_url}';")
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)

    # Verification: Check karo ki kya abhi bhi purana 'Section wise summary' dikh raha hai?
    if page.locator("text=Section wise summary").is_visible():
        print("Website ne wapas summary par bhej diya! Dobara Status menu try kar रहे hain...")
        status_btn = page.locator("a:has-text('Status')")
        if status_btn.count() > 0:
            status_btn.first.click()
            time.sleep(2)
            sub_link = page.locator("a[href*='deviceList']")
            if sub_link.count() > 0:
                sub_link.first.click()
            else:
                page.goto(target_url, wait_until='networkidle')
        time.sleep(5)

def run():
    target_url = 'https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            print("1. Website open ho rahi hai...")
            page.goto(target_url, timeout=60000)
            
            print("2. Login kar rahe hain...")
            page.locator('input[type="text"]').first.fill('sserjk')
            page.locator('input[type="password"]').first.fill('sserjk')
            
            # Enter dabane ke bajaye login button par click ya form submit
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign In")')
            if submit_btn.count() > 0:
                submit_btn.first.click()
            else:
                page.keyboard.press('Enter')
            
            print("3. Dashboard load hone ka wait kar rahe hain...")
            # Jab tak Logout ya Status button na dikhe, tab tak wait karo (yani login pakka ho gaya)
            page.wait_for_selector("text=Logout", timeout=60000)
            page.wait_for_load_state('networkidle', timeout=60000)
            time.sleep(3)
            
            # 4. Ab sahi page par jao aur screenshot lo
            for i in range(1, 3):
                # Har screenshot se pehle confirm karo ki hum deviceListOnly par hi hain
                if "dashboard_deviceListOnly.php" not in page.url or page.locator("text=Section wise summary").is_visible():
                    open_correct_page(page, target_url)
                else:
                    page.reload(wait_until='networkidle', timeout=60000)
                    time.sleep(5)
                
                print(f"Current URL: {page.url}")
                file_name = f'dashboard_screenshot_{int(time.time())}.png'
                page.screenshot(path=file_name, full_page=True)
                print(f"Screenshot saved: {file_name}")
                
                if i == 1:
                    print("2 minute wait...")
                    time.sleep(120)
                    
        except Exception as e:
            print(f"Error aaya: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    run()
