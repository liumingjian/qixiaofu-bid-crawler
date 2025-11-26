from __future__ import annotations
import random
import time
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.config_loader import load_config
from utils.logger import setup_logger

ProgressCallback = Callable[[int, int, Optional[Mapping]], None]


class WeChatArticleScraper:
    """Selenium-based WeChat article scraper with retries and batch support."""

    def __init__(
        self,
        config_path: str | Path = "config.yml",
        *,
        config: Optional[Mapping] = None,
        driver_factory: Optional[Callable[[], webdriver.Chrome]] = None,
        logger=None,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = dict(config) if config else self._load_config(self.config_path)
        scraper_cfg = self.config.get("scraper", {})
        paths_cfg = self.config.get("paths", {})

        self.headless = scraper_cfg.get("headless", True)
        self.wait_time = scraper_cfg.get("wait_time", 5)
        self.retry_count = scraper_cfg.get("retry_count", 3)
        self.retry_delay = scraper_cfg.get("retry_delay", 5)
        self.random_delay_range = tuple(scraper_cfg.get("random_delay_range", (2, 5)))

        self.driver_factory = driver_factory
        log_dir = paths_cfg.get("log_dir", "data/logs")
        self.logger = logger or setup_logger(self.__class__.__name__, log_dir=log_dir)
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self) -> "WeChatArticleScraper":
        self.init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _load_config(self, path: Path) -> Mapping:
        return load_config(path)

    def init_driver(self) -> webdriver.Chrome:
        if self.driver:
            return self.driver

        if self.driver_factory:
            self.driver = self.driver_factory()
            self.logger.info("Driver initialized via custom factory.")
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
            self.logger.info("Chrome driver initialized.")
            return driver
        except Exception as exc:  # pragma: no cover - environment dependent
            self.logger.error("Failed to initialize Chrome driver: %s", exc)
            raise

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed.")
            except Exception as exc:  # pragma: no cover
                self.logger.error("Error closing browser: %s", exc)
            finally:
                self.driver = None

    def scrape_article(self, url: str) -> Optional[dict]:
        driver = self.init_driver()
        try:
            self.logger.debug("Navigating to %s", url)
            driver.get(url)
            time.sleep(self.wait_time)
            self._wait_for_content(driver)
            self.scroll_page()
            html = driver.page_source
            article_data = self.parse_html(html)
            article_data["url"] = url
            return article_data
        except Exception as exc:
            self.logger.error("Error scraping %s: %s", url, exc, exc_info=True)
            return None

    def scrape_articles_batch(
        self, article_urls: Iterable[str], callback: Optional[ProgressCallback] = None
    ) -> List[dict]:
        urls = list(article_urls)
        if not urls:
            return []

        self.init_driver()
        results: List[dict] = []
        total = len(urls)
        failures = 0
        self.logger.info("Starting batch crawl: %d article(s).", total)

        for index, url in enumerate(urls, start=1):
            self.logger.info("Processing %d/%d: %s", index, total, url)
            article_data = self._scrape_with_retry(url)
            if article_data:
                results.append(article_data)
                if callback:
                    callback(index, total, article_data)
            else:
                failures += 1
            self._random_delay()

        success_rate = (len(results) / total * 100) if total else 0
        self.logger.info(
            "Batch crawl complete: %d success, %d failed (%.1f%%).",
            len(results),
            failures,
            success_rate,
        )
        return results

    def _scrape_with_retry(self, url: str) -> Optional[dict]:
        for attempt in range(1, self.retry_count + 1):
            article = self.scrape_article(url)
            if article and article.get("content_text"):
                self.logger.info("Scrape succeeded on attempt %d: %s", attempt, url)
                return article

            self.logger.warning("Attempt %d/%d failed for %s", attempt, self.retry_count, url)
            if attempt < self.retry_count:
                self.logger.info("Retrying in %d seconds...", self.retry_delay)
                time.sleep(self.retry_delay)

        self.logger.error("All attempts failed for %s", url)
        return None

    def _wait_for_content(self, driver) -> None:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "js_content")))
        except Exception:
            self.logger.debug("Content container not detected within wait time.")

    def _random_delay(self) -> None:
        start, end = self.random_delay_range
        if end <= 0:
            return
        delay = random.uniform(start, end)
        self.logger.debug("Sleeping for %.2f seconds.", delay)
        time.sleep(delay)

    def scroll_page(self) -> None:
        if not self.driver:
            return
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            current_position = 0
            while current_position < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(0.3)
                current_position += viewport_height
                total_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception as exc:
            self.logger.warning("Scroll failed: %s", exc)

    @staticmethod
    def parse_html(html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        article_data: dict = {}
        title_tag = soup.find("h1", class_="rich_media_title")
        if title_tag:
            article_data["title"] = title_tag.get_text().strip()

        author_tag = soup.find("a", class_="rich_media_meta_link")
        if not author_tag:
            author_tag = soup.find("span", class_="rich_media_meta_text")
        if author_tag:
            article_data["author"] = author_tag.get_text().strip()

        time_tag = soup.find("em", id="publish_time")
        if time_tag:
            article_data["publish_time"] = time_tag.get_text().strip()

        content_tag = soup.find("div", id="js_content") or soup.find("div", class_="rich_media_content")
        if content_tag:
            article_data["content_text"] = content_tag.get_text().strip()
            article_data["content_html"] = str(content_tag)
            paragraphs = content_tag.find_all(["p", "section"])
            article_data["paragraphs"] = [
                p.get_text().strip() for p in paragraphs if p.get_text().strip()
            ]
            images = content_tag.find_all("img")
            article_data["images"] = []
            for img in images:
                img_url = img.get("data-src") or img.get("src")
                if img_url:
                    article_data["images"].append(img_url)

        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            article_data["description"] = desc_tag.get("content", "")

        return article_data
