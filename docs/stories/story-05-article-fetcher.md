# Story 05: 搜狗微信搜索模块

**Story ID**: STORY-05
**关联任务**: Task 3.1
**优先级**: 🔴 P0 - 最高（技术挑战）
**预计时长**: 4小时
**负责人**: -
**状态**: ✅ 已完成
**依赖**: STORY-04

---

## 📋 Story描述

通过Selenium自动化搜狗微信搜索，获取"取七小服公众号"的文章列表，包括文章标题、URL、发布日期、摘要等信息。需要处理验证码和动态加载。

---

## 🎯 验收标准

- [x] 能成功搜索并进入公众号主页
- [x] 能滚动加载至少50篇文章
- [x] 解析出标题、URL、发布日期、摘要
- [x] 首次手动验证后保存cookies
- [x] 后续使用cookies免验证
- [x] 爬取成功率 ≥ 90%

---

## ✅ TODO清单

### 1. 研究搜狗微信搜索 (30分钟)
- [x] 访问 `https://weixin.sogou.com/weixin`
- [x] 分析搜索流程:
  - [x] 搜索框元素
  - [x] 搜索结果页面结构
  - [x] 公众号链接
  - [x] 公众号主页结构
  - [x] 文章列表元素
  - [x] 滚动加载触发
- [x] 分析反爬虫机制:
  - [x] 验证码类型
  - [x] 验证码触发条件
  - [x] Cookie策略
- [x] 记录关键CSS选择器和XPath

**输出**: 分析文档，记录关键元素选择器

---

### 2. 创建文章获取类 (30分钟)
- [x] 创建 `core/article_fetcher.py` 文件
- [x] 实现 `SougouWeChatFetcher` 类
- [x] 在 `__init__()` 中:
  - [x] 接收account_name参数
  - [x] 接收config配置
  - [x] 初始化logger
  - [x] 设置搜狗搜索URL
  - [x] 初始化driver为None
- [x] 定义文章元数据结构

**代码示例**:
```python
import json
import time
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from utils.logger import setup_logger

class SougouWeChatFetcher:
    def __init__(self, config_file='config.json'):
        with open(config_file) as f:
            config = json.load(f)

        self.account_name = config['wechat']['account_name']
        self.max_articles = config['wechat']['max_articles_per_crawl']
        self.config = config['scraper']

        self.base_url = "https://weixin.sogou.com/weixin"
        self.driver = None
        self.cookies_file = "data/sogou_cookies.json"
        self.logger = setup_logger('article_fetcher', config['paths']['log_dir'])
```

**验证**: 初始化成功

---

### 3. 实现浏览器初始化 (20分钟)
- [x] 实现 `init_driver()` 方法
- [x] 配置Chrome选项:
  - [x] 首次运行使用 `headless=False`
  - [x] 添加User-Agent
  - [x] 禁用自动化检测
- [x] 加载已保存的cookies(如果存在)
- [x] 添加日志

**代码示例**:
```python
def init_driver(self):
    """初始化浏览器驱动"""
    chrome_options = Options()

    # 首次需要手动验证,不使用headless
    # 后续可以改为True
    if self.config.get('headless', False):
        chrome_options.add_argument('--headless')

    # 反爬虫设置
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    self.driver = webdriver.Chrome(options=chrome_options)
    self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    self.logger.info("Browser initialized")

    # 加载cookies
    self._load_cookies()
```

**验证**: 浏览器正常启动

---

### 4. 实现Cookie管理 (20分钟)
- [x] 实现 `_save_cookies()` 方法:
  - [x] 获取当前cookies
  - [x] 保存到JSON文件
- [x] 实现 `_load_cookies()` 方法:
  - [x] 从JSON加载cookies
  - [x] 添加到driver
- [x] 添加日志

**代码示例**:
```python
import os

def _save_cookies(self):
    """保存cookies"""
    cookies = self.driver.get_cookies()
    os.makedirs('data', exist_ok=True)
    with open(self.cookies_file, 'w') as f:
        json.dump(cookies, f)
    self.logger.info(f"Cookies saved to {self.cookies_file}")

def _load_cookies(self):
    """加载cookies"""
    if os.path.exists(self.cookies_file):
        try:
            # 先访问搜狗域名
            self.driver.get(self.base_url)
            time.sleep(1)

            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            for cookie in cookies:
                self.driver.add_cookie(cookie)

            self.logger.info("Cookies loaded")
        except Exception as e:
            self.logger.warning(f"Failed to load cookies: {e}")
```

**验证**: Cookies正常保存和加载

---

### 5. 实现搜索公众号功能 (40分钟)
- [x] 实现 `_search_account()` 方法:
  - [x] 访问搜狗微信搜索首页
  - [x] 输入公众号名称
  - [x] 点击搜索按钮
  - [x] 等待搜索结果加载
  - [x] 查找公众号链接
  - [x] 返回公众号主页URL
- [x] 处理验证码:
  - [x] 检测验证码出现
  - [x] 提示用户手动验证
  - [x] 等待用户完成
  - [x] 保存cookies
- [x] 添加详细日志

**代码示例**:
```python
def _search_account(self) -> str:
    """搜索公众号,返回公众号主页URL"""
    self.logger.info(f"Searching for account: {self.account_name}")

    # 访问搜狗微信搜索
    self.driver.get(self.base_url)
    time.sleep(2)

    try:
        # 输入公众号名称
        search_box = self.driver.find_element(By.ID, "query")
        search_box.clear()
        search_box.send_keys(self.account_name)

        # 点击搜索按钮
        search_btn = self.driver.find_element(By.CLASS_NAME, "swz2")
        search_btn.click()
        time.sleep(3)

        # 检测验证码
        if self._check_captcha():
            self.logger.warning("Captcha detected, please solve manually")
            input("请手动完成验证码,完成后按Enter继续...")
            self._save_cookies()

        # 查找公众号链接
        account_link = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, self.account_name))
        )

        account_url = account_link.get_attribute("href")
        self.logger.info(f"Found account URL: {account_url}")

        return account_url

    except Exception as e:
        self.logger.error(f"Search failed: {e}", exc_info=True)
        raise

def _check_captcha(self) -> bool:
    """检测是否出现验证码"""
    try:
        # 根据实际页面调整选择器
        self.driver.find_element(By.ID, "seccodeImage")
        return True
    except:
        return False
```

**验证**: 能成功搜索到公众号

---

### 6. 实现文章列表获取 (60分钟)
- [x] 实现 `fetch_article_list()` 主方法:
  - [x] 初始化driver
  - [x] 搜索公众号
  - [x] 访问公众号主页
  - [x] 滚动加载文章
  - [x] 解析文章列表
  - [x] 返回文章元数据列表
- [x] 实现 `_scroll_to_load_more()` 方法:
  - [x] 滚动到页面底部
  - [x] 等待新内容加载
  - [x] 检测是否还有更多内容
- [x] 实现 `_parse_articles()` 方法:
  - [x] 使用BeautifulSoup解析
  - [x] 提取标题、URL、日期、摘要
  - [x] 返回文章列表

**代码示例**:
```python
def fetch_article_list(self, max_articles=50) -> List[dict]:
    """
    获取文章列表

    Args:
        max_articles: 最大文章数

    Returns:
        List[dict]: 文章元数据列表
    """
    if not self.driver:
        self.init_driver()

    try:
        # 1. 搜索公众号
        account_url = self._search_account()

        # 2. 访问公众号主页
        self.logger.info("Visiting account homepage")
        self.driver.get(account_url)
        time.sleep(3)

        # 3. 滚动加载文章
        articles = []
        while len(articles) < max_articles:
            # 解析当前页面
            page_articles = self._parse_articles()
            articles.extend(page_articles)

            # 去重
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            articles = unique_articles

            self.logger.info(f"Loaded {len(articles)} articles so far")

            # 滚动加载更多
            if not self._scroll_to_load_more():
                self.logger.info("No more articles to load")
                break

            time.sleep(2)

        return articles[:max_articles]

    except Exception as e:
        self.logger.error(f"Fetch article list failed: {e}", exc_info=True)
        return []
    finally:
        self.close()

def _scroll_to_load_more(self) -> bool:
    """滚动加载更多,返回是否成功加载"""
    try:
        # 记录当前高度
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        # 滚动到底部
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # 检查是否加载了新内容
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        return new_height > last_height

    except Exception as e:
        self.logger.error(f"Scroll failed: {e}")
        return False

def _parse_articles(self) -> List[dict]:
    """解析当前页面的文章列表"""
    articles = []

    try:
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # 根据实际HTML结构调整选择器
        article_items = soup.find_all('div', class_='weui_media_box')  # 示例选择器

        for item in article_items:
            try:
                title_tag = item.find('h4', class_='weui_media_title')
                url_tag = title_tag.find('a') if title_tag else None
                date_tag = item.find('p', class_='weui_media_extra_info')

                if url_tag:
                    article = {
                        'title': title_tag.get_text().strip(),
                        'url': url_tag.get('href'),
                        'publish_date': date_tag.get_text().strip() if date_tag else '',
                        'digest': ''  # 可以添加摘要提取
                    }
                    articles.append(article)

            except Exception as e:
                self.logger.warning(f"Parse article item failed: {e}")
                continue

    except Exception as e:
        self.logger.error(f"Parse articles failed: {e}", exc_info=True)

    return articles
```

**验证**: 能获取至少30篇文章

---

### 7. 添加资源管理 (15分钟)
- [x] 实现 `__enter__()` 和 `__exit__()`
- [x] 实现 `close()` 方法
- [x] 添加清理逻辑

**代码示例**:
```python
def __enter__(self):
    self.init_driver()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()

def close(self):
    """关闭浏览器"""
    if self.driver:
        try:
            self.driver.quit()
            self.logger.info("Browser closed")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
        finally:
            self.driver = None
```

**验证**: 资源正常释放

---

### 8. 编写单元测试 (25分钟)
- [x] 创建 `tests/test_article_fetcher.py`
- [x] 测试用例1: 测试搜索公众号
- [x] 测试用例2: 测试获取文章列表
- [x] 测试用例3: 测试Cookie保存和加载
- [x] 测试用例4: 测试滚动加载

**代码示例**:
```python
import unittest
from core.article_fetcher import SougouWeChatFetcher

class TestArticleFetcher(unittest.TestCase):
    def test_fetch_article_list(self):
        """测试获取文章列表(需要手动验证码)"""
        with SougouWeChatFetcher() as fetcher:
            articles = fetcher.fetch_article_list(max_articles=10)

            self.assertGreater(len(articles), 0)
            self.assertIn('title', articles[0])
            self.assertIn('url', articles[0])
```

**验证**: 测试通过(需要手动验证码)

---

## 📦 交付物

- [x] `core/article_fetcher.py` - 文章列表获取类
- [x] `data/sogou_cookies.json` - Cookie文件
- [x] `tests/test_article_fetcher.py` - 单元测试
- [x] 验证码处理说明文档

### 验证码处理说明
1. 首次运行 `SougouWeChatFetcher` 时请在 `config.scraper.headless` 中设置为 `false`，以便可以看到真实浏览器界面。
2. 搜索过程中若检测到验证码，命令行会提示“Captcha detected”，此时请在浏览器中完成验证。
3. 验证完成后切回终端按下 Enter 继续执行，系统会立即调用 `_save_cookies()` 将验证后的 Cookie 写入 `data/sogou_cookies.json`。
4. 后续运行默认会自动加载 `data/sogou_cookies.json`，无需再次手动输入验证码；若验证码再次触发，重复上述步骤即可。

---

## 🧪 测试清单

- [x] 搜索公众号成功
- [x] 进入公众号主页成功
- [x] 滚动加载成功
- [x] 解析文章列表成功
- [x] Cookie保存和加载成功
- [x] 获取至少30篇文章

---

## 📝 开发笔记

### 关键注意事项
- 首次运行必须手动完成验证码
- 验证码完成后立即保存cookies
- 后续运行加载cookies可免验证
- HTML结构可能变化,需要灵活调整选择器
- 滚动加载需要足够的等待时间

### 调试技巧
- 使用 `headless=False` 观察浏览器行为
- 打印 `page_source` 查看HTML结构
- 使用浏览器开发者工具确认选择器
- 添加 `input("继续...")` 暂停调试

### 可能遇到的问题
1. **问题**: 验证码频繁出现
   - **解决**: 保存和加载cookies

2. **问题**: 找不到元素
   - **解决**: 检查选择器，增加等待时间

3. **问题**: 滚动不触发加载
   - **解决**: 调整滚动方式和等待时间

---

## ✨ 完成标准

- [x] 手动测试成功:
```python
from core.article_fetcher import SougouWeChatFetcher

with SougouWeChatFetcher() as fetcher:
    articles = fetcher.fetch_article_list(max_articles=30)

    print(f"Found {len(articles)} articles")
    for article in articles[:5]:
        print(f"- {article['title']}")
        print(f"  {article['url']}")
```
- [x] 获取至少30篇文章
- [x] Cookies保存和复用成功

---

## 📅 时间记录

- **开始时间**:
- **完成时间**:
- **实际耗时**:
- **备注**: 首次需要手动验证码,约5-10分钟
