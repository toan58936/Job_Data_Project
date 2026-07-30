"""
Standalone script debug đăng nhập ITviec qua Playwright — bản chẩn đoán chi tiết.

Khác bản gốc: KHÔNG gói toàn bộ trong 1 try/except (nuốt hết lỗi thành 1 dòng
chung chung). Mỗi bước có log riêng + chụp screenshot/dump HTML khi fail, để biết
CHÍNH XÁC bước nào hỏng thay vì đoán.

Usage: E:\\job-data-project\\.venv\\Scripts\\python.exe crawler/scripts/login_itviec.py
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, "E:/job-data-project/crawler")

DEBUG_DIR = Path("E:/job-data-project/data/metadata/login_debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def _dump_debug(page, step: str):
    """Chụp screenshot + lưu HTML hiện tại khi 1 bước fail — để xem THẬT trang
    đang ở trạng thái nào, không đoán."""
    try:
        screenshot_path = DEBUG_DIR / f"fail_{step}.png"
        html_path = DEBUG_DIR / f"fail_{step}.html"
        page.screenshot(path=str(screenshot_path))
        html_path.write_text(page.content(), encoding="utf-8")
        print(f"  -> Đã lưu debug: {screenshot_path} và {html_path}")
        print(f"  -> URL hiện tại: {page.url}")
        print(f"  -> Page title: {page.title()}")
    except Exception as e:
        print(f"  -> (Không chụp được debug: {e})")


def main():
    email = os.environ.get("ITVIEC_EMAIL")
    password = os.environ.get("ITVIEC_PASSWORD")

    if not email or not password:
        print("ERROR: ITVIEC_EMAIL và ITVIEC_PASSWORD chưa set")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: chưa cài playwright — pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        # headless=False để bạn TỰ MẮT xem trình duyệt làm gì khi debug lần đầu
        # (đổi lại True sau khi đã xác nhận chạy đúng)
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # ---- Bước 1: mở trang login ----
        print("[1/6] Mở https://itviec.com/users/sign_in ...")
        try:
            page.goto("https://itviec.com/users/sign_in", timeout=30000, wait_until="domcontentloaded")
            # KHÔNG dùng wait_for_load_state("networkidle") -- site có tracking script
            # chạy nền liên tục, networkidle rất dễ không bao giờ đạt được -> treo/timeout
            # oan dù trang đã load xong đủ để thao tác.
            print(f"  -> OK. URL: {page.url}")
        except Exception as e:
            print(f"  -> LỖI ở bước mở trang: {e}")
            _dump_debug(page, "step1_goto")
            browser.close()
            sys.exit(1)

        # ---- Bước 2: tìm ô email ----
        print("[2/6] Tìm ô nhập email...")
        email_selectors = [
            'input[name="user[email]"]',
            'input[type="email"]',
            'input#user_email',
            'input[placeholder*="mail" i]',
        ]
        email_input = None
        for sel in email_selectors:
            try:
                page.wait_for_selector(sel, timeout=5000)
                email_input = sel
                print(f"  -> Khớp selector: {sel}")
                break
            except Exception:
                continue
        if not email_input:
            print("  -> LỖI: không tìm thấy ô email với bất kỳ selector nào đã thử.")
            _dump_debug(page, "step2_email_not_found")
            print("  -> Mở file HTML/screenshot vừa lưu để tìm đúng selector thật, "
                  "sau đó cập nhật email_selectors ở trên.")
            browser.close()
            sys.exit(1)

        # ---- Bước 3: điền form ----
        print("[3/6] Điền email + password...")
        try:
            page.fill(email_input, email)
            password_selectors = ['input[name="user[password]"]', 'input[type="password"]']
            password_input = None
            for sel in password_selectors:
                if page.locator(sel).count() > 0:
                    password_input = sel
                    break
            if not password_input:
                raise RuntimeError("Không tìm thấy ô password")
            page.fill(password_input, password)
            print(f"  -> OK. password selector: {password_input}")
        except Exception as e:
            print(f"  -> LỖI ở bước điền form: {e}")
            _dump_debug(page, "step3_fill_form")
            browser.close()
            sys.exit(1)

        # ---- Bước 4: click submit ----
        print("[4/6] Click nút đăng nhập...")
        submit_selectors = ['button[type="submit"]', 'input[type="submit"]']
        clicked = False
        for sel in submit_selectors:
            try:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    clicked = True
                    print(f"  -> Đã click: {sel}")
                    break
            except Exception:
                continue
        if not clicked:
            print("  -> LỖI: không click được nút submit nào.")
            _dump_debug(page, "step4_submit")
            browser.close()
            sys.exit(1)

        # ---- Bước 5: chờ redirect sau login, không giả định URL cụ thể ----
        print("[5/6] Chờ trang chuyển hướng sau khi submit...")
        try:
            page.wait_for_timeout(4000)  # chờ cứng 4s thay vì đoán URL đích
            print(f"  -> URL sau khi submit: {page.url}")
            print(f"  -> Page title: {page.title()}")
        except Exception as e:
            print(f"  -> LỖI khi chờ: {e}")
            _dump_debug(page, "step5_wait_after_submit")

        # ---- Bước 6: kiểm tra cookie session ----
        print("[6/6] Kiểm tra cookie session...")
        cookies = context.cookies()
        itviec_cookies = {c["name"]: c["value"] for c in cookies if "itviec.com" in c["domain"]}
        print(f"  -> Tổng cookie itviec.com: {len(itviec_cookies)}")
        print(f"  -> Tên các cookie: {list(itviec_cookies.keys())}")

        has_session = any("session" in name.lower() for name in itviec_cookies)

        if not has_session:
            print("  -> CHƯA thấy cookie session -> login CHƯA thành công thật sự.")
            _dump_debug(page, "step6_no_session")
            print("  -> Xem screenshot/HTML vừa lưu để biết trang đang hiện gì "
                  "(có thể còn ở trang login với thông báo lỗi sai mật khẩu, "
                  "hoặc gặp captcha/2FA chưa xử lý).")
            browser.close()
            sys.exit(1)

        cookies_path = Path("E:/job-data-project/data/metadata/itviec_cookies.json")
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies_path.write_text(
            json.dumps(itviec_cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"THÀNH CÔNG — cookie đã lưu tại {cookies_path}")
        browser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()