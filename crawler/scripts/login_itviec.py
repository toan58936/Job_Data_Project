"""
Standalone script debug đăng nhập ITviec qua Playwright — bản chẩn đoán chi tiết (v2 — đã fix).

FIX so với bản gốc:
1. URL login SAI: https://itviec.com/users/sign_in KHÔNG tồn tại (site trả trang lỗi tuỳ chỉnh
   "Oops! This page has found a better job" nhưng vẫn trả HTTP 200 -> script cũ không phát hiện
   được vì chỉ check exception, không check nội dung/tiêu đề trang).
   URL ĐÚNG: https://itviec.com/sign_in (đã verify trực tiếp 31/07/2026).
2. Thêm bước kiểm tra 404/trang lỗi NGAY sau goto — để lần sau nếu site đổi URL lần nữa,
   script báo lỗi rõ ràng ở bước 1 thay vì clam lặng lẽ tới bước 2 mới báo "không tìm thấy ô email".
3. Selector email/password: ưu tiên tìm theo LABEL TEXT ("Email", "Password") trước — ổn định hơn
   selector theo tên attribute Rails cũ (user[email]) vì trang có thể đã đổi sang React/SPA.
4. Tiêu chí "login thành công": không chỉ dựa vào tên cookie chứa "session" (mong manh, có thể đổi
   tên bất kỳ lúc nào) — thêm kiểm tra phụ: nút "Sign In with Email" / form login còn hiển thị hay
   không sau khi submit.
"""
import os
import sys
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "crawler"))

DEBUG_DIR = _PROJECT_ROOT / "data" / "metadata" / "login_debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

LOGIN_URL = "https://itviec.com/sign_in"   # <-- ĐÃ SỬA, trước đây là /users/sign_in (404)

# Dấu hiệu nhận biết trang lỗi 404 tuỳ chỉnh của ITviec (dù HTTP status vẫn 200)
NOT_FOUND_MARKERS = [
    "found a better job",
    "doesn't exist",
    "Oops!",
]


def _dump_debug(page, step: str):
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


def _looks_like_404(page) -> bool:
    title = (page.title() or "").lower()
    body_snippet = page.locator("body").inner_text()[:500].lower()
    return any(m.lower() in title or m.lower() in body_snippet for m in NOT_FOUND_MARKERS)


def main():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

    email = os.environ.get("ITVIEC_EMAIL")
    password = os.environ.get("ITVIEC_PASSWORD")

    if not email or not password:
        print("ERROR: ITVIEC_EMAIL và ITVIEC_PASSWORD chưa set. Hãy kiểm tra file .env ở gốc dự án.")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: chưa cài playwright — pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
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
        print(f"[1/7] Mở {LOGIN_URL} ...")
        try:
            page.goto(LOGIN_URL, timeout=30000, wait_until="domcontentloaded")
            # Chờ thêm 1 chút cho phần header/form React hydrate xong (trang có vẻ dùng SPA
            # cho phần menu) trước khi kết luận là 404 hay không.
            page.wait_for_timeout(1500)
            print(f"  -> URL: {page.url}")
            print(f"  -> Title: {page.title()}")
        except Exception as e:
            print(f"  -> LỖI ở bước mở trang: {e}")
            _dump_debug(page, "step1_goto")
            browser.close()
            sys.exit(1)

        # ---- Bước mới: kiểm tra 404 NGAY, không đợi tới bước tìm ô email mới phát hiện ----
        print("[2/7] Kiểm tra trang có phải trang lỗi 404 không...")
        if _looks_like_404(page):
            print(f"  -> LỖI: {LOGIN_URL} trả về trang lỗi (title: '{page.title()}').")
            print("  -> ITviec có thể đã đổi URL login lần nữa. Kiểm tra lại bằng cách vào "
                  "https://itviec.com và bấm nút Sign In để lấy URL thật hiện tại, "
                  "rồi cập nhật biến LOGIN_URL ở đầu file.")
            _dump_debug(page, "step2_404")
            browser.close()
            sys.exit(1)
        print("  -> OK, không phải trang lỗi.")

        # ---- Bước 3: tìm ô email — ưu tiên label text trước, CSS selector sau ----
        print("[3/7] Tìm ô nhập email...")
        email_input_locator = None

        # Chiến lược A: theo label (ổn định nhất, không phụ thuộc tên attribute)
        try:
            candidate = page.get_by_label("Email", exact=False).first
            candidate.wait_for(timeout=5000)
            email_input_locator = candidate
            print("  -> Khớp theo label 'Email'")
        except Exception:
            pass

        # Chiến lược B: fallback CSS selector (giữ danh sách cũ + mở rộng thêm vài biến thể)
        if email_input_locator is None:
            email_selectors = [
                'input[name="user[email]"]',
                'input[name="email"]',
                'input[type="email"]',
                'input#user_email',
                'input[placeholder*="mail" i]',
            ]
            for sel in email_selectors:
                try:
                    page.wait_for_selector(sel, timeout=3000)
                    email_input_locator = page.locator(sel).first
                    print(f"  -> Khớp selector CSS: {sel}")
                    break
                except Exception:
                    continue

        if email_input_locator is None:
            print("  -> LỖI: không tìm thấy ô email bằng cả label lẫn CSS selector.")
            _dump_debug(page, "step3_email_not_found")
            print("  -> Mở file HTML/screenshot vừa lưu để tìm đúng selector thật.")
            browser.close()
            sys.exit(1)

        # ---- Bước 4: điền form ----
        print("[4/7] Điền email + password...")
        try:
            email_input_locator.fill(email)

            password_input_locator = None
            try:
                candidate = page.get_by_label("Password", exact=False).first
                candidate.wait_for(timeout=5000)
                password_input_locator = candidate
                print("  -> Khớp password theo label 'Password'")
            except Exception:
                for sel in ['input[name="user[password]"]', 'input[name="password"]', 'input[type="password"]']:
                    if page.locator(sel).count() > 0:
                        password_input_locator = page.locator(sel).first
                        print(f"  -> Khớp password theo CSS: {sel}")
                        break

            if password_input_locator is None:
                raise RuntimeError("Không tìm thấy ô password bằng cả label lẫn CSS selector")
            password_input_locator.fill(password)
            print("  -> OK.")
        except Exception as e:
            print(f"  -> LỖI ở bước điền form: {e}")
            _dump_debug(page, "step4_fill_form")
            browser.close()
            sys.exit(1)

        # ---- Bước 5: click submit — ưu tiên tìm theo text nút thật ("Sign In with Email") ----
        print("[5/7] Click nút đăng nhập...")
        clicked = False
        try:
            btn = page.get_by_role("button", name="Sign In with Email", exact=False).first
            btn.wait_for(timeout=5000)
            btn.click()
            clicked = True
            print("  -> Đã click nút 'Sign In with Email'")
        except Exception:
            for sel in ['button[type="submit"]', 'input[type="submit"]']:
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
            _dump_debug(page, "step5_submit")
            browser.close()
            sys.exit(1)

        # ---- Bước 6: chờ redirect sau login ----
        print("[6/7] Chờ trang chuyển hướng sau khi submit...")
        try:
            page.wait_for_timeout(4000)
            print(f"  -> URL sau khi submit: {page.url}")
            print(f"  -> Page title: {page.title()}")
        except Exception as e:
            print(f"  -> LỖI khi chờ: {e}")
            _dump_debug(page, "step6_wait_after_submit")

        # ---- Bước 7: kiểm tra đã login thật hay chưa (2 tiêu chí, không chỉ dựa cookie) ----
        print("[7/7] Kiểm tra trạng thái đăng nhập...")
        cookies = context.cookies()
        itviec_cookies = {c["name"]: c["value"] for c in cookies if "itviec.com" in c["domain"]}
        print(f"  -> Tổng cookie itviec.com: {len(itviec_cookies)}")
        print(f"  -> Tên các cookie: {list(itviec_cookies.keys())}")

        has_session_cookie = any("session" in name.lower() for name in itviec_cookies)

        # Tiêu chí phụ: nếu form login (nút "Sign In with Email") KHÔNG còn trên trang -> có
        # khả năng đã login thành công (site không redirect sang URL khác mà load lại nội dung).
        still_on_login_form = False
        try:
            still_on_login_form = page.get_by_role("button", name="Sign In with Email", exact=False).first.is_visible(timeout=2000)
        except Exception:
            still_on_login_form = False

        login_success = has_session_cookie and not still_on_login_form

        if not login_success:
            print("  -> CHƯA xác nhận login thành công.")
            print(f"     - has_session_cookie = {has_session_cookie}")
            print(f"     - still_on_login_form = {still_on_login_form}")
            _dump_debug(page, "step7_login_uncertain")
            print("  -> Xem screenshot/HTML để biết trang đang hiện gì (sai mật khẩu, "
                  "captcha, 2FA, hoặc yêu cầu xác nhận email...).")
            browser.close()
            sys.exit(1)

        cookies_path = _PROJECT_ROOT / "data" / "metadata" / "itviec_cookies.json"
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies_path.write_text(
            json.dumps(itviec_cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"THÀNH CÔNG — cookie đã lưu tại {cookies_path}")
        browser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()