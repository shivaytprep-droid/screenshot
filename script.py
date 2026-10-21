import time
import subprocess
from playwright.sync_api import sync_playwright

def open_correct_page(page, target_url):
    link = page.locator("a[href*='dashboard_deviceListOnly.php']")
    if link.count() > 0:
        link.first.click(force=True)
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)
    else:
        page.evaluate(f"window.location.href = '{target_url}';")
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)

    if page.locator("text=Section wise summary").is_visible():
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

def push_to_github(file_name):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "add", file_name], check=False)
        subprocess.run(["git", "commit", "-m", f"Auto screenshot: {file_name}"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)
        print(f"GitHub par turant upload ho gaya: {file_name}")
    except Exception as e:
        print(f"Git push error: {e}")

def run():
    target_url = 'https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            page.goto(target_url, timeout=60000)
            page.locator('input[type="text"]').first.fill('sserjk')
            page.locator('input[type="password"]').first.fill('sserjk')
            
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign In")')
            if submit_btn.count() > 0:
                submit_btn.first.click()
            else:
                page.keyboard.press('Enter')
            
            page.wait_for_selector("text=Logout", timeout=60000)
            page.wait_for_load_state('networkidle', timeout=60000)
            time.sleep(3)
            
            # 1 ghante tak lagatar har 2 minute me screenshot (30 times)
            for i in range(1, 31):
                start_time = time.time()
                
                # Check ki kahin session logout to nahi ho gaya
                if page.locator('input[type="password"]').is_visible():
                    page.locator('input[type="text"]').first.fill('sserjk')
                    page.locator('input[type="password"]').first.fill('sserjk')
                    page.keyboard.press('Enter')
                    page.wait_for_selector("text=Logout", timeout=60000)
                    time.sleep(3)

                if "dashboard_deviceListOnly.php" not in page.url or page.locator("text=Section wise summary").is_visible():
                    open_correct_page(page, target_url)
                else:
                    page.reload(wait_until='networkidle', timeout=60000)
                    time.sleep(5)
                
                file_name = f'dashboard_screenshot_{int(time.time())}.png'
                page.screenshot(path=file_name, full_page=True)
                print(f"[{i}/30] Screenshot saved: {file_name}")
                
                # Lete hi turant GitHub par push karo
                push_to_github(file_name)
                
                if i < 30:
                    # Exact 120 seconds (2 min) ka gap maintain karna
                    elapsed = time.time() - start_time
                    sleep_time = max(10, 120 - elapsed)
                    print(f"Agla screenshot {int(sleep_time)} second baad...")
                    time.sleep(sleep_time)
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    run()
