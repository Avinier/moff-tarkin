import random
import time
import asyncio
from typing import Dict, Any, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None
try:
    import pyppeteer
    from pyppeteer_stealth import stealth
except ImportError:
    pyppeteer = None
    stealth = None
import httpx
import tls_client
from fake_useragent import UserAgent
from loguru import logger

class StealthBrowser:
    """Advanced browser with anti-detection features"""

    def __init__(self, browser_type: str = "chrome", proxy: Optional[str] = None):
        self.browser_type = browser_type
        self.proxy = proxy
        self.ua = UserAgent()
        self.session = None

    async def create_undetected_chrome(self) -> uc.Chrome:
        """Create undetected Chrome instance"""
        options = uc.ChromeOptions()

        # Stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Random viewport
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        options.add_argument(f'--window-size={width},{height}')

        # Disable WebRTC
        options.add_experimental_option("prefs", {
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False
        })

        # Random user agent
        user_agent = self.ua.random
        options.add_argument(f'user-agent={user_agent}')

        # Proxy settings
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        # Additional stealth
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')

        driver = uc.Chrome(options=options, version_main=120)

        # Execute stealth JavaScript
        await self._inject_stealth_js(driver)

        return driver

    async def create_playwright_browser(self):
        """Create Playwright browser with stealth"""
        playwright = await async_playwright().start()

        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]

        if self.proxy:
            proxy_config = {"server": self.proxy}
        else:
            proxy_config = None

        if self.browser_type == "chromium":
            browser = await playwright.chromium.launch(
                headless=False,
                args=browser_args,
                proxy=proxy_config
            )
        elif self.browser_type == "firefox":
            browser = await playwright.firefox.launch(
                headless=False,
                proxy=proxy_config
            )
        else:
            browser = await playwright.webkit.launch(
                headless=False,
                proxy=proxy_config
            )

        context = await browser.new_context(
            viewport={'width': random.randint(1366, 1920),
                     'height': random.randint(768, 1080)},
            user_agent=self.ua.random,
            locale='en-US',
            timezone_id='America/New_York'
        )

        page = await context.new_page()
        if stealth_async:
            await stealth_async(page)

        return browser, context, page

    async def create_pyppeteer_browser(self):
        """Create Pyppeteer browser with stealth"""
        if not pyppeteer:
            logger.warning("Pyppeteer not available, skipping")
            return None, None

        browser = await pyppeteer.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                f'--proxy-server={self.proxy}' if self.proxy else ''
            ]
        )

        page = await browser.newPage()
        if stealth:
            await stealth(page)

        # Set random viewport
        await page.setViewport({
            'width': random.randint(1366, 1920),
            'height': random.randint(768, 1080)
        })

        # Set random user agent
        await page.setUserAgent(self.ua.random)

        return browser, page

    async def _inject_stealth_js(self, driver):
        """Inject JavaScript to evade detection"""
        stealth_js = """
        // Override navigator properties
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );

        // Canvas fingerprint protection
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
            const data = getImageData.call(this, sx, sy, sw, sh);
            for (let i = 0; i < data.data.length; i += 4) {
                data.data[i] = data.data[i] ^ (Math.random() * 0.1);
            }
            return data;
        };

        // WebGL fingerprint protection
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };

        // Chrome runtime
        window.chrome = {runtime: {}};

        // Console.debug protection
        const originalConsoleDebug = console.debug;
        console.debug = function(...args) {
            if (!args[0]?.includes('DevTools')) {
                return originalConsoleDebug.apply(console, args);
            }
        };
        """
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': stealth_js
        })

class ProxyRotator:
    """Manage proxy rotation with health checking"""

    def __init__(self, proxies: list):
        self.proxies = proxies
        self.working_proxies = []
        self.failed_proxies = set()
        self.current_index = 0

    async def get_proxy(self) -> str:
        """Get next working proxy"""
        if not self.working_proxies:
            await self.test_proxies()

        if not self.working_proxies:
            logger.warning("No working proxies available")
            return None

        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy

    async def test_proxies(self):
        """Test all proxies for connectivity"""
        logger.info(f"Testing {len(self.proxies)} proxies...")

        async def test_proxy(proxy):
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy, "https://": proxy},
                    timeout=10
                ) as client:
                    response = await client.get("http://httpbin.org/ip")
                    if response.status_code == 200:
                        return proxy
            except:
                pass
            return None

        tasks = [test_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks)

        self.working_proxies = [p for p in results if p]
        logger.info(f"Found {len(self.working_proxies)} working proxies")

    def mark_failed(self, proxy: str):
        """Mark proxy as failed"""
        self.failed_proxies.add(proxy)
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)

class HumanBehavior:
    """Simulate human-like behavior"""

    @staticmethod
    async def random_delay(min_seconds: float = 0.5, max_seconds: float = 3.0):
        """Random delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    @staticmethod
    async def human_typing(element, text: str):
        """Type text with human-like delays"""
        for char in text:
            element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.3))

    @staticmethod
    async def random_mouse_movement(driver):
        """Simulate random mouse movements"""
        action = ActionChains(driver)

        for _ in range(random.randint(2, 5)):
            x = random.randint(0, 1000)
            y = random.randint(0, 800)
            action.move_by_offset(x, y)
            action.pause(random.uniform(0.1, 0.5))

        action.perform()

    @staticmethod
    async def random_scroll(driver):
        """Random page scrolling"""
        scroll_count = random.randint(1, 3)
        for _ in range(scroll_count):
            scroll_amount = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

class TLSClient:
    """TLS fingerprint evasion client"""

    def __init__(self, client_identifier: str = "chrome_120"):
        self.session = tls_client.Session(
            client_identifier=client_identifier,
            random_tls_extension_order=True
        )
        self.session.headers.update({
            "User-Agent": UserAgent().random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request with TLS evasion"""
        return self.session.get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request with TLS evasion"""
        return self.session.post(url, **kwargs)