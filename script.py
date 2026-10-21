import os
import time
import subprocess
import requests
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

# ==========================================
# YAHAN APNA TELEGRAM TOKEN AUR CHAT ID DALEIN
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# Indian Standard Time (IST = UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def send_to_telegram(file_path, caption):
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN" or not TELEGRAM_BOT_TOKEN:
        print("Telegram Token set nahi hai, skip kar rahe hain...")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(file_path, 'rb') as photo:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            files = {'photo': photo}
            r = requests.post(url, data=payload, files=files, timeout=30)
            if r.status_code == 200:
                print("Telegram par screenshot bhej diya gaya!")
            else:
                print(f"Telegram API Error: {r.text}")
    except Exception as e:
        print(f"Telegram fail ho gaya: {e}")

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

def push_to_github(file_path):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "add", file_path], check=False)
        subprocess.run(["git", "commit", "-m", f"Auto screenshot: {file_path}"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)
        print(f"GitHub par datewise folder me upload ho gaya: {file_path}")
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
            
            for i in range(1, 31):
                start_time = time.time()
                
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
                
                # IST Date aur Time nikalna
                now_ist = datetime.now(IST)
                date_folder = now_ist.strftime('%Y-%m-%d')
                time_str = now_ist.strftime('%H-%M-%S')
                
                # Datewise folder banana (e.g., 2026-10-21)
                os.makedirs(date_folder, exist_ok=True)
                
                file_path = f"{date_folder}/screenshot_{time_str}.png"
                page.screenshot(path=file_path, full_page=True)
                print(f"[{i}/30] Screenshot saved: {file_path}")
                
                # 1. GitHub ke Datewise folder me push karna
                push_to_github(file_path)
                
                # 2. Telegram par photo aur exact time bhejna
                caption = f"📊 RJK Device List\n📅 Date: {date_folder}\n⏰ Time: {now_ist.strftime('%I:%M:%S %p')}"
                send_to_telegram(file_path, caption)
                
                if i < 30:
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
