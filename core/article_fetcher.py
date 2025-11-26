"""Sogou WeChat article list fetcher."""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Callable, List, Mapping, MutableMapping, Optional, Sequence

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import setup_logger


ArticleData = MutableMapping[str, str]


class SougouWeChatFetcher:
    """Fetch the latest article list of a WeChat account via Sogou search."""

    base_url = "https://weixin.sogou.com/weixin"

    def __init__(
        self,
        config_path: str | Path = "config.json",
        *,
        config: Optional[Mapping] = None,
        driver_factory: Optional[Callable[[], webdriver.Chrome]] = None,
        logger=None,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = dict(config) if config else self._load_config(self.config_path)
        self.driver_factory = driver_factory

        wechat_cfg = self.config.get("wechat", {})
        scraper_cfg = self.config.get("scraper", {})
        paths_cfg = self.config.get("paths", {})

        self.account_name = wechat_cfg.get("account_name", "")
        self.max_articles = wechat_cfg.get("max_articles_per_crawl", 50)

        self.wait_time = scraper_cfg.get("wait_time", 5)
        self.retry_count = scraper_cfg.get("retry_count", 3)
        self.retry_delay = scraper_cfg.get("retry_delay", 5)
        self.random_delay_range: Sequence[float] = tuple(
            scraper_cfg.get("random_delay_range", (2, 5))
        )
        self.headless = scraper_cfg.get("headless", False)
        self.prompt_on_captcha = scraper_cfg.get("prompt_on_captcha", True)

        data_dir = Path(paths_cfg.get("data_dir", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        log_dir = Path(paths_cfg.get("log_dir", "data/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)

        self.cookies_file = data_dir / "sogou_cookies.json"
        self.logger = logger or setup_logger(self.__class__.__name__, log_dir=log_dir)
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self) -> "SougouWeChatFetcher":
        self.init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _load_config(self, path: Path) -> Mapping:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def init_driver(self) -> webdriver.Chrome:
        """Initialise the Chrome driver and inject anti-detection scripts."""
        if self.driver:
            return self.driver

        if self.driver_factory:
            self.driver = self.driver_factory()
            self.logger.info("Driver initialised via custom factory.")
            return self.driver

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    """
                },
            )
            self.driver = driver
            self.logger.info("Chrome driver initialised.")
            self._load_cookies()
            return driver
        except Exception as exc:  # pragma: no cover - environment dependent
            self.logger.error("Failed to initialise Chrome driver: %s", exc)
            raise

    def close(self) -> None:
        """Close and reset the driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed.")
            except Exception as exc:  # pragma: no cover
                self.logger.error("Error closing browser: %s", exc)
            finally:
                self.driver = None

    def fetch_article_list(self, max_articles: Optional[int] = None) -> List[ArticleData]:
        """
        Fetch article metadata from the target WeChat account via Sogou search.

        Args:
            max_articles: Optional override of the maximum number of articles.
        """
        limit = max_articles or self.max_articles
        if limit <= 0:
            return []

        driver = self.init_driver()
        articles: List[ArticleData] = []
        seen_urls: set[str] = set()

        try:
            account_url = self._search_account()
            self.logger.info("Opening account homepage: %s", account_url)
            driver.get(account_url)
            time.sleep(2)

            while len(articles) < limit:
                parsed = self._parse_articles()
                new_added = 0
                for article in parsed:
                    url = article.get("url")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    articles.append(article)
                    new_added += 1
                    if len(articles) >= limit:
                        break

                self.logger.info(
                    "Parsed %d new article(s); total collected: %d", new_added, len(articles)
                )

                if len(articles) >= limit:
                    break

                if not self._scroll_to_load_more():
                    self.logger.info("No more content to load.")
                    break

                self._random_delay()

        except Exception as exc:
            self.logger.error("Failed to fetch article list: %s", exc, exc_info=True)
            return []

        return articles[:limit]

    def _random_delay(self) -> None:
        start, end = self.random_delay_range if self.random_delay_range else (0, 0)
        if end <= 0:
            return
        delay = random.uniform(start, end)
        self.logger.debug("Sleeping for %.2fs before next action.", delay)
        time.sleep(delay)

    def _search_account(self) -> str:
        """Search the configured account name and return its homepage URL."""
        driver = self.init_driver()
        driver.get(self.base_url)
        self.logger.info("Searching account: %s", self.account_name)

        search_box = self._find_element_safe(
            [(By.ID, "query"), (By.NAME, "query"), (By.CSS_SELECTOR, "input#query")]
        )
        if not search_box:
            raise RuntimeError("Search box not found on Sogou page.")

        search_box.clear()
        search_box.send_keys(self.account_name)

        search_button = self._find_element_safe(
            [
                (By.CLASS_NAME, "swz2"),
                (By.CLASS_NAME, "swz"),
                (By.CSS_SELECTOR, "button.swz"),
                (By.CSS_SELECTOR, "input.swz"),
            ]
        )
        if search_button:
            search_button.click()
        else:
            search_box.submit()
        time.sleep(2)

        self._handle_captcha_if_needed()

        locator = (
            By.XPATH,
            f"//a[contains(@uigs,'account_name') and contains(normalize-space(.), '{self.account_name}')]",
        )
        account_link = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located(locator)
        )
        url = account_link.get_attribute("href")
        if not url:
            raise RuntimeError("Account URL not found in search results.")
        return url

    def _handle_captcha_if_needed(self) -> None:
        if not self._check_captcha():
            return
        self.logger.warning("Captcha detected. Please solve it manually in the browser window.")
        if self.prompt_on_captcha:
            input("Solve the captcha in the browser. Press Enter to continue...")
        self._save_cookies()

    def _check_captcha(self) -> bool:
        if not self.driver:
            return False
        captcha_selectors = [
            (By.ID, "seccodeImage"),
            (By.CLASS_NAME, "verifycode"),
            (By.CSS_SELECTOR, "img#seccodeImage"),
        ]
        for by, value in captcha_selectors:
            try:
                self.driver.find_element(by, value)
                return True
            except Exception:
                continue
        return False

    def _find_element_safe(self, locators: Sequence[tuple[str, str]]):
        if not self.driver:
            return None
        for by, value in locators:
            try:
                element = self.driver.find_element(by, value)
                if element:
                    return element
            except Exception:
                continue
        return None

    def _scroll_to_load_more(self) -> bool:
        """Scroll down to trigger the lazy loading of more articles."""
        if not self.driver:
            return False
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            return bool(new_height and new_height > last_height)
        except Exception as exc:
            self.logger.error("Scroll failed: %s", exc)
            return False

    def _parse_articles(self) -> List[ArticleData]:
        if not self.driver:
            return []
        return self._parse_articles_from_html(self.driver.page_source)

    def _parse_articles_from_html(self, html: str) -> List[ArticleData]:
        """Parse article metadata from the provided HTML snippet."""
        soup = BeautifulSoup(html, "html.parser")
        articles: List[ArticleData] = []

        # Prefer outer list items to avoid duplicate parsing against inner blocks.
        items = soup.select("ul.news-list li")
        if not items:
            items = soup.select("div.txt-box")
        if not items:
            items = soup.select("div.weui_media_box")

        for item in items:
            node = item
            if item.name == "li":
                inner = item.select_one("div.txt-box")
                if inner:
                    node = inner
            try:
                title_tag = node.select_one("h3 a") or node.select_one("h4 a")
                if not title_tag:
                    continue
                url = title_tag.get("href")
                title = title_tag.get_text(strip=True)
                digest_tag = node.select_one("p.txt-info") or node.select_one("p.weui_media_desc")
                date_tag = node.select_one("span.s2") or node.select_one("p.weui_media_extra_info")

                articles.append(
                    {
                        "title": title,
                        "url": url or "",
                        "publish_date": date_tag.get_text(strip=True) if date_tag else "",
                        "digest": digest_tag.get_text(strip=True) if digest_tag else "",
                    }
                )
            except Exception as exc:
                self.logger.debug("Failed to parse article item: %s", exc)
                continue

        return articles

    def _load_cookies(self) -> None:
        if not self.driver or not self.cookies_file.exists():
            return
        try:
            self.driver.get(self.base_url)
            time.sleep(1)
            with self.cookies_file.open("r", encoding="utf-8") as fp:
                cookies = json.load(fp)
            for cookie in cookies:
                if "expiry" in cookie and isinstance(cookie["expiry"], float):
                    cookie["expiry"] = int(cookie["expiry"])
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    continue
            self.logger.info("Cookies loaded from %s", self.cookies_file)
        except Exception as exc:
            self.logger.warning("Failed to load cookies: %s", exc)

    def _save_cookies(self) -> None:
        if not self.driver:
            return
        try:
            cookies = self.driver.get_cookies()
            with self.cookies_file.open("w", encoding="utf-8") as fp:
                json.dump(cookies, fp, ensure_ascii=False, indent=2)
            self.logger.info("Cookies saved to %s", self.cookies_file)
        except Exception as exc:
            self.logger.warning("Failed to save cookies: %s", exc)
