import os
import time
import subprocess
import requests
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

# GitHub Secrets ya Environment Variable se token aur chat id uthana
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "971307814")

IST = timezone(timedelta(hours=5, minutes=30))

def send_to_telegram(file_path, caption):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("⚠️ Telegram Token set nahi hai ya empty hai! Secrets check karein.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(file_path, 'rb') as photo:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            files = {'photo': photo}
            r = requests.post(url, data=payload, files=files, timeout=40)
            if r.status_code == 200:
                print("✅ Telegram par photo bhej di gayi!")
            else:
                print(f"❌ Telegram API Error: Status {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Telegram Request Failed: {e}")

def open_correct_page(page, target_url):
    page.goto(target_url, wait_until='networkidle', timeout=60000)
    time.sleep(4)

    if page.locator("text=Section wise summary").is_visible():
        link = page.locator("a[href*='dashboard_deviceListOnly.php']")
        if link.count() > 0:
            link.first.click(force=True)
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
                page.wait_for_load_state('networkidle', timeout=60000)
                time.sleep(5)

def push_to_github(file_path):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "add", file_path], check=False)
        subprocess.run(["git", "commit", "-m", f"Added: {file_path}"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)
        print(f"GitHub folder me save ho gaya: {file_path}")
    except Exception as e:
        print(f"Git push error: {e}")

def run():
    target_url = 'https://ip3.rilapp.com/railways/dashboard_deviceListOnly.php'
    count = 1
    
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
            
            # Unlimited Loop
            while True:
                start_time = time.time()
                
                # Agar session expire hokar login page wapas aa jaye
                if page.locator('input[type="password"]').is_visible():
                    page.locator('input[type="text"]').first.fill('sserjk')
                    page.locator('input[type="password"]').first.fill('sserjk')
                    page.keyboard.press('Enter')
                    page.wait_for_selector("text=Logout", timeout=60000)
                    time.sleep(3)

                open_correct_page(page, target_url)
                
                now_ist = datetime.now(IST)
                date_folder = now_ist.strftime('%Y-%m-%d')
                time_str = now_ist.strftime('%H-%M-%S')
                
                os.makedirs(date_folder, exist_ok=True)
                file_path = f"{date_folder}/screenshot_{time_str}.png"
                
                page.screenshot(path=file_path, full_page=True)
                print(f"[#{count}] Saved: {file_path}")
                
                push_to_github(file_path)
                
                caption = f"📊 RJK Device List\n📅 Date: {date_folder}\n⏰ Time: {now_ist.strftime('%I:%M:%S %p')}"
                send_to_telegram(file_path, caption)
                
                count += 1
                
                # 2 minute ka interval maintain karna
                elapsed = time.time() - start_time
                sleep_time = max(10, 120 - elapsed)
                time.sleep(sleep_time)
                    
        except Exception as e:
            print(f"Loop interrupted: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    run()
