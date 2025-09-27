import asyncio
import base64
from typing import Optional, Dict, Any
try:
    from twocaptcha import TwoCaptcha
except ImportError:
    TwoCaptcha = None
try:
    from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
    from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless
except ImportError:
    recaptchaV2Proxyless = None
    hCaptchaProxyless = None
from loguru import logger
import httpx

class CaptchaSolver:
    """Multi-service captcha solving"""

    def __init__(self, twocaptcha_key: str = None, anticaptcha_key: str = None):
        self.twocaptcha = TwoCaptcha(twocaptcha_key) if (twocaptcha_key and TwoCaptcha) else None
        self.anticaptcha_key = anticaptcha_key

    async def solve_recaptcha_v2(self, sitekey: str, url: str, service: str = "auto") -> Optional[str]:
        """Solve reCAPTCHA v2"""
        if service == "2captcha" and self.twocaptcha:
            return await self._solve_2captcha_v2(sitekey, url)
        elif service == "anticaptcha" and self.anticaptcha_key:
            return await self._solve_anticaptcha_v2(sitekey, url)
        else:
            # Try all available services
            if self.twocaptcha:
                result = await self._solve_2captcha_v2(sitekey, url)
                if result:
                    return result
            if self.anticaptcha_key:
                result = await self._solve_anticaptcha_v2(sitekey, url)
                if result:
                    return result
        return None

    async def _solve_2captcha_v2(self, sitekey: str, url: str) -> Optional[str]:
        """Solve using 2captcha"""
        try:
            logger.info("Solving reCAPTCHA v2 with 2captcha...")
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.twocaptcha.recaptcha(sitekey=sitekey, url=url)
            )
            logger.success("Captcha solved successfully")
            return result['code']
        except Exception as e:
            logger.error(f"2captcha failed: {e}")
            return None

    async def _solve_anticaptcha_v2(self, sitekey: str, url: str) -> Optional[str]:
        """Solve using AntiCaptcha"""
        try:
            logger.info("Solving reCAPTCHA v2 with AntiCaptcha...")
            solver = recaptchaV2Proxyless()
            solver.set_key(self.anticaptcha_key)
            solver.set_website_url(url)
            solver.set_website_key(sitekey)

            g_response = await asyncio.get_event_loop().run_in_executor(
                None,
                solver.solve_and_return_solution
            )

            if g_response:
                logger.success("Captcha solved successfully")
                return g_response
        except Exception as e:
            logger.error(f"AntiCaptcha failed: {e}")
            return None

    async def solve_recaptcha_v3(self, sitekey: str, url: str, action: str = "submit",
                                  min_score: float = 0.7) -> Optional[str]:
        """Solve reCAPTCHA v3"""
        if self.twocaptcha:
            try:
                logger.info("Solving reCAPTCHA v3...")
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.twocaptcha.recaptcha(
                        sitekey=sitekey,
                        url=url,
                        version='v3',
                        action=action,
                        score=min_score
                    )
                )
                return result['code']
            except Exception as e:
                logger.error(f"reCAPTCHA v3 solving failed: {e}")
        return None

    async def solve_hcaptcha(self, sitekey: str, url: str) -> Optional[str]:
        """Solve hCaptcha"""
        if self.anticaptcha_key:
            try:
                logger.info("Solving hCaptcha...")
                solver = hCaptchaProxyless()
                solver.set_key(self.anticaptcha_key)
                solver.set_website_url(url)
                solver.set_website_key(sitekey)

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    solver.solve_and_return_solution
                )

                if result:
                    logger.success("hCaptcha solved successfully")
                    return result
            except Exception as e:
                logger.error(f"hCaptcha solving failed: {e}")

        if self.twocaptcha:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.twocaptcha.hcaptcha(sitekey=sitekey, url=url)
                )
                return result['code']
            except Exception as e:
                logger.error(f"hCaptcha solving with 2captcha failed: {e}")

        return None

    async def solve_cloudflare_turnstile(self, sitekey: str, url: str) -> Optional[str]:
        """Solve Cloudflare Turnstile"""
        if self.twocaptcha:
            try:
                logger.info("Solving Cloudflare Turnstile...")
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.twocaptcha.turnstile(sitekey=sitekey, url=url)
                )
                return result['code']
            except Exception as e:
                logger.error(f"Turnstile solving failed: {e}")
        return None

    async def solve_image_captcha(self, image_path: str) -> Optional[str]:
        """Solve image-based captcha"""
        if self.twocaptcha:
            try:
                logger.info("Solving image captcha...")
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.twocaptcha.normal(image_path)
                )
                return result['code']
            except Exception as e:
                logger.error(f"Image captcha solving failed: {e}")
        return None

class CloudflareBypasser:
    """Bypass Cloudflare protection"""

    def __init__(self):
        self.session = None

    async def bypass_cloudflare(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Bypass Cloudflare and return cookies"""
        try:
            import cloudscraper

            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )

            if proxy:
                scraper.proxies = {
                    'http': proxy,
                    'https': proxy
                }

            response = scraper.get(url)

            if response.status_code == 200:
                logger.success("Cloudflare bypassed successfully")
                return {
                    'cookies': scraper.cookies.get_dict(),
                    'user_agent': scraper.headers['User-Agent'],
                    'content': response.text
                }
        except Exception as e:
            logger.error(f"Cloudflare bypass failed: {e}")

        # Fallback to FlareSolverr if available
        return await self._use_flaresolverr(url, proxy)

    async def _use_flaresolverr(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Use FlareSolverr service for bypass"""
        try:
            flaresolverr_url = "http://localhost:8191/v1"  # Default FlareSolverr endpoint

            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000
            }

            if proxy:
                payload["proxy"] = proxy

            async with httpx.AsyncClient() as client:
                response = await client.post(f"{flaresolverr_url}", json=payload)
                data = response.json()

                if data.get("status") == "ok":
                    logger.success("Cloudflare bypassed with FlareSolverr")
                    solution = data["solution"]
                    return {
                        'cookies': solution["cookies"],
                        'user_agent': solution["userAgent"],
                        'content': solution["response"]
                    }
        except Exception as e:
            logger.error(f"FlareSolverr bypass failed: {e}")

        return None