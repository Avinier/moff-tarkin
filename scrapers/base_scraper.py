import asyncio
import random
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
import json
from datetime import datetime
import sys
sys.path.append('..')

from utils.antidetect import StealthBrowser, ProxyRotator, HumanBehavior, TLSClient
from utils.captcha_solver import CaptchaSolver, CloudflareBypasser
from config.settings import PROXY_CONFIG, STEALTH_CONFIG, CAPTCHA_CONFIG, USER_AGENTS

class BaseScraper(ABC):
    """Base scraper with anti-detection and aggressive extraction"""

    def __init__(self, name: str, use_browser: bool = False):
        self.name = name
        self.use_browser = use_browser
        self.proxies = self._load_proxies()
        self.proxy_rotator = ProxyRotator(self.proxies) if self.proxies else None
        self.captcha_solver = CaptchaSolver(
            twocaptcha_key=CAPTCHA_CONFIG.get('2captcha_key'),
            anticaptcha_key=CAPTCHA_CONFIG.get('anticaptcha_key')
        )
        self.cloudflare_bypasser = CloudflareBypasser()
        self.tls_client = TLSClient()
        self.session_cache = {}
        self.failed_urls = set()
        self.success_count = 0
        self.fail_count = 0

    def _load_proxies(self) -> List[str]:
        """Load proxy list from config"""
        proxies = []
        providers = PROXY_CONFIG.get('providers', {})
        for provider, proxy_str in providers.items():
            if proxy_str:
                proxies.append(proxy_str)
        return proxies

    async def fetch(self, url: str, method: str = "GET", **kwargs) -> Optional[str]:
        """Aggressively fetch URL with multiple fallback methods"""

        # Try cache first
        cache_key = hashlib.md5(f"{url}:{method}".encode()).hexdigest()
        if cache_key in self.session_cache:
            logger.debug(f"Using cached response for {url}")
            return self.session_cache[cache_key]

        # Method 1: TLS Client with proxy rotation
        content = await self._fetch_tls_client(url, method, **kwargs)
        if content:
            self.session_cache[cache_key] = content
            return content

        # Method 2: Cloudscraper for Cloudflare
        content = await self._fetch_cloudscraper(url)
        if content:
            self.session_cache[cache_key] = content
            return content

        # Method 3: Browser automation
        if self.use_browser:
            content = await self._fetch_browser(url)
            if content:
                self.session_cache[cache_key] = content
                return content

        # Method 4: Standard httpx with aggressive retry
        content = await self._fetch_httpx(url, method, **kwargs)
        if content:
            self.session_cache[cache_key] = content
            return content

        self.failed_urls.add(url)
        logger.error(f"All fetch methods failed for {url}")
        return None

    async def _fetch_tls_client(self, url: str, method: str = "GET", **kwargs) -> Optional[str]:
        """Fetch using TLS fingerprint evasion"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                proxy = await self.proxy_rotator.get_proxy() if self.proxy_rotator else None

                if proxy:
                    self.tls_client.session.proxies = {
                        "http": proxy,
                        "https": proxy
                    }

                # Randomize headers
                self.tls_client.session.headers.update({
                    "User-Agent": random.choice(USER_AGENTS),
                    "Referer": f"https://www.google.com/search?q={url.split('/')[2]}"
                })

                if method == "GET":
                    response = await self.tls_client.get(url, **kwargs)
                else:
                    response = await self.tls_client.post(url, **kwargs)

                if response.status_code == 200:
                    self.success_count += 1
                    logger.success(f"TLS client fetch successful: {url}")
                    return response.text

                if response.status_code == 403:
                    logger.warning(f"403 Forbidden, trying Cloudflare bypass: {url}")
                    return None

            except Exception as e:
                logger.debug(f"TLS client attempt {attempt + 1} failed: {e}")
                if proxy and self.proxy_rotator:
                    self.proxy_rotator.mark_failed(proxy)

        return None

    async def _fetch_cloudscraper(self, url: str) -> Optional[str]:
        """Use cloudscraper for Cloudflare bypass"""
        try:
            proxy = await self.proxy_rotator.get_proxy() if self.proxy_rotator else None
            result = await self.cloudflare_bypasser.bypass_cloudflare(url, proxy)

            if result:
                self.success_count += 1
                logger.success(f"Cloudflare bypass successful: {url}")
                return result['content']
        except Exception as e:
            logger.debug(f"Cloudscraper failed: {e}")

        return None

    async def _fetch_browser(self, url: str) -> Optional[str]:
        """Fetch using automated browser with stealth"""
        try:
            proxy = await self.proxy_rotator.get_proxy() if self.proxy_rotator else None
            browser = StealthBrowser(browser_type="chrome", proxy=proxy)

            # Use undetected Chrome
            driver = await browser.create_undetected_chrome()

            # Navigate with human-like behavior
            driver.get(url)
            await HumanBehavior.random_delay(2, 5)
            await HumanBehavior.random_scroll(driver)
            await HumanBehavior.random_mouse_movement(driver)

            # Check for captcha
            if self._detect_captcha(driver.page_source):
                await self._solve_page_captcha(driver)
                await HumanBehavior.random_delay(2, 4)

            # Get page content
            content = driver.page_source
            driver.quit()

            self.success_count += 1
            logger.success(f"Browser fetch successful: {url}")
            return content

        except Exception as e:
            logger.debug(f"Browser fetch failed: {e}")
            try:
                driver.quit()
            except:
                pass

        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
    async def _fetch_httpx(self, url: str, method: str = "GET", **kwargs) -> Optional[str]:
        """Standard HTTP client with aggressive retry"""
        proxy = await self.proxy_rotator.get_proxy() if self.proxy_rotator else None

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

        proxy_dict = None
        if proxy:
            proxy_dict = {"http://": proxy, "https://": proxy}

        client_kwargs = {
            "headers": headers,
            "timeout": 30,
            "follow_redirects": True,
            "verify": False  # Ignore SSL errors
        }

        if proxy_dict:
            client_kwargs["proxy"] = proxy

        async with httpx.AsyncClient(**client_kwargs) as client:

            if method == "GET":
                response = await client.get(url, **kwargs)
            else:
                response = await client.post(url, **kwargs)

            if response.status_code == 200:
                self.success_count += 1
                return response.text

            raise httpx.HTTPError(f"Status {response.status_code}")

    def _detect_captcha(self, html: str) -> bool:
        """Detect if page contains captcha"""
        captcha_indicators = [
            'g-recaptcha',
            'h-captcha',
            'cf-turnstile',
            'captcha',
            'challenge-form',
            '/recaptcha/api',
            'hcaptcha.com'
        ]
        return any(indicator in html.lower() for indicator in captcha_indicators)

    async def _solve_page_captcha(self, driver):
        """Attempt to solve captcha on page"""
        try:
            # Try to find reCAPTCHA
            if driver.find_elements("css selector", ".g-recaptcha"):
                sitekey = driver.find_element("css selector", ".g-recaptcha").get_attribute("data-sitekey")
                solution = await self.captcha_solver.solve_recaptcha_v2(sitekey, driver.current_url)
                if solution:
                    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solution}";')
                    driver.execute_script('document.getElementById("captcha-form").submit();')
                    logger.success("reCAPTCHA solved and submitted")

            # Try to find hCaptcha
            elif driver.find_elements("css selector", ".h-captcha"):
                sitekey = driver.find_element("css selector", ".h-captcha").get_attribute("data-sitekey")
                solution = await self.captcha_solver.solve_hcaptcha(sitekey, driver.current_url)
                if solution:
                    driver.execute_script(f'document.getElementsByName("h-captcha-response")[0].innerHTML="{solution}";')
                    driver.execute_script('document.getElementsByName("g-recaptcha-response")[0].innerHTML="{solution}";')
                    logger.success("hCaptcha solved")

        except Exception as e:
            logger.error(f"Captcha solving failed: {e}")

    async def parse(self, html: str) -> Dict[str, Any]:
        """Parse HTML content"""
        soup = BeautifulSoup(html, 'lxml')
        return {
            'title': soup.title.string if soup.title else None,
            'text': soup.get_text(),
            'soup': soup
        }

    @abstractmethod
    async def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape specific URL - to be implemented by subclasses"""
        pass

    async def batch_scrape(self, urls: List[str], max_concurrent: int = 20) -> List[Dict[str, Any]]:
        """Aggressively scrape multiple URLs concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url):
            async with semaphore:
                try:
                    return await self.scrape(url)
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    return None

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

        # Filter out None results
        valid_results = [r for r in results if r is not None]

        logger.info(f"Batch scrape complete: {len(valid_results)}/{len(urls)} successful")
        logger.info(f"Success rate: {self.success_count}/{self.success_count + self.fail_count}")

        return valid_results

    def save_raw(self, url: str, content: str):
        """Save raw content to disk for later processing"""
        from pathlib import Path
        import hashlib

        filename = hashlib.md5(url.encode()).hexdigest()
        filepath = Path(f"data/raw/{self.name}/{filename}.html")
        filepath.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            'url': url,
            'scraper': self.name,
            'timestamp': datetime.now().isoformat(),
            'success': True
        }

        # Save HTML
        filepath.write_text(content, encoding='utf-8')

        # Save metadata
        meta_path = filepath.with_suffix('.json')
        meta_path.write_text(json.dumps(metadata, indent=2))

        logger.debug(f"Saved raw content to {filepath}")