"""
LoginMiddleware – authenticates to ITviec (Stimulus.js login form)
by reading session cookies from a pre-saved JSON file.

The cookies file is produced by a separate Playwright script run
outside Scrapy's event loop (e.g. crawler/scripts/login_itviec.py).

If the cookies file is missing or stale, the middleware disables itself
gracefully and crawling continues without authentication (salary will
show as AUTH_GATED).
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
    Scrapy's async context.
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

            page.goto("https://itviec.com/users/sign_in", timeout=30000)
            page.wait_for_load_state("networkidle")

            page.wait_for_selector(
                'input[name="user[email]"]', timeout=15000
            )

            page.fill('input[name="user[email]"]', email)
            page.fill('input[name="user[password]"]', password)
            page.click('button[type="submit"]')

            page.wait_for_url("**/it-jobs/**", timeout=15000)
            page.wait_for_load_state("networkidle")

            cookies = context.cookies()
            itviec_cookies = {
                c["name"]: c["value"]
                for c in cookies
                if c["domain"] == "itviec.com"
            }

            has_session = any(
                "session" in c["name"].lower()
                for c in cookies
                if c["domain"] == "itviec.com"
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
    """Middleware that attaches pre-saved ITviec session cookies to
    Scrapy requests.  The cookies must be saved to disk first (see
    crawler/scripts/login_itviec.py or LoginMiddleware.login_via_playwright())."""

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
        """Load session cookies from the pre-saved JSON file."""
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
                    "Loaded %d ITviec session cookies from %s",
                    len(self.cookie_dict),
                    path,
                )
            else:
                logger.warning(
                    "ITviec cookies file is empty — crawling unauthenticated"
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load ITviec cookies: %s", exc)

    def process_request(self, request, spider): # Đã thêm tham số spider để hết cảnh báo
        if self.spider is None or self.spider.name != "itviec_detail":
            return None
        if not self.logged_in or not self.cookie_dict:
            return None
            
        # 1. Gán cookie cho Scrapy request thuần
        request.cookies = self.cookie_dict
        
        # 2. Ép cookie vào Playwright Browser Context (BẮT BUỘC cho Playwright)
        formatted_cookies = [
            {"name": k, "value": v, "domain": ".itviec.com", "path": "/"}
            for k, v in self.cookie_dict.items()
        ]
        request.meta.setdefault("playwright_context_kwargs", {})["cookies"] = formatted_cookies
        
        return None

    def process_response(self, request, response, spider): # Đã thêm tham số spider
        if self.spider is None or self.spider.name != "itviec_detail":
            return response
        if response.status != 200:
            return response

        if (
            b"Sign in to view salary" in response.body
            and "sign_in" not in response.url
        ):
            if self.logged_in:
                # SỬA LỖI TRUYỀN THAM SỐ CHO CLOSESPIDER BẰNG F-STRING
                raise CloseSpider(
                    f"Auth-gated salary detected on {response.url} — session expired. "
                    f"Re-run crawler/scripts/login_itviec.py to refresh cookies, "
                    f"then restart the crawl."
                )
            else:
                logger.warning(
                    "Detected auth-gated salary on %s — not logged in, "
                    "crawling unauthenticated",
                    response.url,
                )
        return response

# ========== THÊM MIDDLEWARE MỚI ==========
class ForcePlaywrightMiddleware:
    """Thêm playwright=True vào mọi request của spider topcv_listing và topcv_detail"""
    def process_request(self, request, spider):
        if spider.name in ["topcv_listing", "topcv_detail"]:
            request.meta.setdefault("playwright", True)
        return None