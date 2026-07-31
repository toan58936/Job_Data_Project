"""
LoginMiddleware – authenticates to ITviec by reading pre-saved session
cookies and attaching them to the "itviec_authed" Playwright context
(defined in settings.py via PLAYWRIGHT_CONTEXTS / storage_state).

The cookies file is produced by a separate Playwright script run outside
Scrapy's event loop (crawler/scripts/login_itviec.py).

If the cookies file is missing or stale, the middleware disables itself
gracefully and crawling continues without authentication (salary will
show as AUTH_GATED).

[FIX — xem giải thích chi tiết trong settings.py]
Trước đây middleware set request.cookies = self.cookie_dict trực tiếp.
scrapy-playwright (0.0.48) nhận diện request.cookies và cố truyền thẳng
vào Browser.new_context(cookies=...) — nhưng Playwright (1.61.0) không có
tham số `cookies` ở new_context() (chỉ có `storage_state`) -> crash ngay
lúc tạo context cho MỌI request itviec_detail:
    TypeError: Browser.new_context() got an unexpected keyword argument 'cookies'

Sửa: không đụng request.cookies nữa. Cookie đã được nạp sẵn 1 lần lúc
khởi động vào context "itviec_authed" qua storage_state (settings.py).
Middleware chỉ cần gán request.meta["playwright_context"] = "itviec_authed"
để request dùng đúng context đã có cookie đó.
"""
import json
import logging
import random
from pathlib import Path

from scrapy import signals
from scrapy.exceptions import CloseSpider
from scrapy.http import Request

logger = logging.getLogger(__name__)


def _cookies_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "metadata" / "itviec_cookies.json"


def login_via_playwright(email: str, password: str) -> bool:
    """Run Playwright headless browser to log in and save cookies to disk.

    Intended to be called from a standalone script or CLI, NOT from inside
    Scrapy's async context. Dùng crawler/scripts/login_itviec.py để debug —
    hàm này giữ lại để có thể gọi programmatically nếu cần (ví dụ từ 1 job
    scheduler tự động refresh cookie định kỳ).

    [FIX] URL login cũ https://itviec.com/users/sign_in trả về trang lỗi 404
    tuỳ chỉnh của ITviec (nhưng vẫn HTTP 200, nên không tự phát hiện được nếu
    không check nội dung). URL đúng: https://itviec.com/sign_in (verify 31/07/2026).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright not installed — cannot login. "
            "Install with: pip install playwright && playwright install chromium"
        )
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            page.goto("https://itviec.com/sign_in", timeout=30000)  # [FIX] URL đúng
            page.wait_for_load_state("networkidle")

            # [FIX] Selector cũ dựa vào tên attribute Rails cũ (user[email]) —
            # ưu tiên tìm theo label text trước, ổn định hơn nếu site đổi tên field.
            try:
                email_input = page.get_by_label("Email", exact=False).first
                email_input.wait_for(timeout=10000)
            except Exception:
                page.wait_for_selector('input[name="user[email]"]', timeout=15000)
                email_input = page.locator('input[name="user[email]"]').first

            email_input.fill(email)

            try:
                password_input = page.get_by_label("Password", exact=False).first
                password_input.wait_for(timeout=5000)
            except Exception:
                password_input = page.locator('input[name="user[password]"]').first
            password_input.fill(password)

            try:
                page.get_by_role("button", name="Sign In with Email", exact=False).first.click()
            except Exception:
                page.click('button[type="submit"]')

            page.wait_for_timeout(4000)
            page.wait_for_load_state("networkidle")

            cookies = context.cookies()
            itviec_cookies = {
                c["name"]: c["value"]
                for c in cookies
                if "itviec.com" in c["domain"]
            }

            has_session = any(
                "session" in c["name"].lower()
                for c in cookies
                if "itviec.com" in c["domain"]
            )

            browser.close()

            if has_session:
                cookies_path = _cookies_path()
                cookies_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cookies_path, "w", encoding="utf-8") as f:
                    json.dump(
                        itviec_cookies, f, ensure_ascii=False, indent=2
                    )
                logger.info(
                    "Login successful — cookies saved to %s", cookies_path
                )
                return True
            else:
                logger.warning(
                    "Login completed but no session cookie found"
                )
                return False

    except Exception as exc:
        logger.error("Playwright login failed: %s", exc)
        return False


class RotatingUserAgentMiddleware:
    """Chọn ngẫu nhiên User-Agent từ danh sách cho mỗi request."""

    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getlist("USER_AGENT_LIST", []))

    def process_request(self, request, spider):
        if self.user_agents:
            request.headers["User-Agent"] = random.choice(self.user_agents)


class LoginMiddleware:
    """Middleware gắn context Playwright đã có sẵn cookie login ITviec
    (context "itviec_authed", được nạp cookie qua storage_state lúc khởi
    động trong settings.py) vào mọi request của spider itviec_detail.

    [FIX] Không còn set request.cookies trực tiếp — xem lý do ở đầu file."""

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.crawler = None
        self.spider = None
        self.cookie_dict = {}
        self.logged_in = False

    @classmethod
    def from_crawler(cls, crawler):
        email = crawler.settings.get("ITVIEC_EMAIL")
        password = crawler.settings.get("ITVIEC_PASSWORD")
        if not email or not password:
            logger.warning(
                "ITVIEC_EMAIL/PASSWORD not set — LoginMiddleware disabled. "
                "Crawling without authentication (salary will be AUTH_GATED)."
            )
            return None
        middleware = cls(email, password)
        crawler.signals.connect(
            middleware.spider_opened, signal=signals.spider_opened
        )
        middleware.crawler = crawler
        return middleware

    def spider_opened(self, spider):
        self.spider = spider
        if spider.name == "itviec_detail":
            self._load_cookies()

    def _load_cookies(self):
        """Load session cookies from the pre-saved JSON file — chỉ dùng để
        biết có nên bật auth hay không (self.logged_in), KHÔNG dùng để set
        request.cookies nữa. Cookie thật đã được nạp vào context
        "itviec_authed" qua storage_state trong settings.py."""
        path = _cookies_path()
        if not path.exists():
            logger.warning(
                "No ITviec cookies file at %s — crawling without authentication. "
                "Run: python crawler/scripts/login_itviec.py",
                path,
            )
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.cookie_dict = json.load(f)
            if self.cookie_dict:
                self.logged_in = True
                logger.info(
                    "Loaded %d ITviec session cookies from %s "
                    "(sẽ dùng context 'itviec_authed' cho mọi request detail)",
                    len(self.cookie_dict),
                    path,
                )
            else:
                logger.warning(
                    "ITviec cookies file is empty — crawling unauthenticated"
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load ITviec cookies: %s", exc)

    def process_request(self, request):
        if self.spider is None or self.spider.name != "itviec_detail":
            return None
        if not self.logged_in or not self.cookie_dict:
            return None
        # [FIX] Không set request.cookies nữa (nguyên nhân crash — xem đầu file).
        # Chỉ trỏ request này dùng context đã có sẵn cookie login.
        request.meta["playwright_context"] = "itviec_authed"
        return None

    def process_response(self, request, response):
        if self.spider is None or self.spider.name != "itviec_detail":
            return response
        if response.status != 200:
            return response

        # [FIX] Chỉ check auth-gated trên request detail THẬT (có job_id trong
        # meta — do parse_detail() set qua scrapy.Request(meta={"job_id": ...})).
        # Request seed (start_urls = "https://itviec.com/it-jobs", dùng để đọc
        # file JSONL và tạo request detail) KHÔNG có job_id -> bỏ qua, tránh
        # false positive: trang listing công khai luôn có chữ
        # "Sign in to view salary" cho các job người xem chưa đăng nhập,
        # không liên quan gì đến việc cookie đăng nhập của mình có hết hạn hay không.
        if "job_id" not in request.meta:
            return response

        if (
            b"Sign in to view salary" in response.body
            and "sign_in" not in response.url
        ):
            if self.logged_in:
                # [FIX] CloseSpider chỉ nhận 1 tham số reason (str) — trước đây
                # truyền kiểu %-format 2 tham số rời (giống logger.warning) gây
                # TypeError. Format chuỗi trước rồi mới truyền vào.
                raise CloseSpider(
                    "Auth-gated salary detected on {} — session expired. "
                    "Re-run crawler/scripts/login_itviec.py to refresh cookies, "
                    "then restart the crawl.".format(response.url)
                )
            else:
                logger.warning(
                    "Detected auth-gated salary on %s — not logged in, "
                    "crawling unauthenticated",
                    response.url,
                )
        return response


class ForcePlaywrightMiddleware:
    """Thêm playwright=True vào mọi request của spider topcv_listing và topcv_detail"""
    def process_request(self, request, spider):
        if spider.name in ["topcv_listing", "topcv_detail"]:
            request.meta.setdefault("playwright", True)
        return None