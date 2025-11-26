import requests
import json
import time
import random
import os
import math
from tqdm import tqdm

def load_config():
    """Load configuration from config.json."""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

import re
from bs4 import BeautifulSoup

def get_article_detail(url, config):
    """Fetch and parse article detail."""
    headers = {
        "Cookie": config.get('cookie', ""),
        "User-Agent": config.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        # Heuristic extraction using Regex
        info = {
            "project_name": "N/A",
            "budget": "N/A",
            "purchaser": "N/A",
            "obtain_docs": "N/A"
        }
        
        # Project Name
        # Often in title or "项目名称："
        # We'll rely on the list title for now, or try to find it in text
        # Regex for Project Name
        match = re.search(r"项目名称[：:]\s*([^\n\r]+)", text)
        if match:
            info["project_name"] = match.group(1).strip()
            
        # Budget
        match = re.search(r"(预算金额|最高限价|采购预算)[：:]\s*([^\n\r]+)", text)
        if match:
            info["budget"] = match.group(2).strip()
            
        # Purchaser
        match = re.search(r"(采购人|招标人)[：:]\s*([^\n\r]+)", text)
        if match:
            info["purchaser"] = match.group(2).strip()
            
        # Obtain Documents
        match = re.search(r"(获取采购文件|招标文件获取|报名时间)[：:]\s*([^\n\r]+)", text)
        if match:
            info["obtain_docs"] = match.group(2).strip()
            
        return info
        
    except Exception as e:
        print(f"Error fetching detail {url}: {e}")
        return None

def get_content_list(total_count, config, per_page=5):
    """
    Fetch all articles based on the total count.
    Matches the logic from the user's screenshot.
    """
    url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
    
    headers = {
        "Cookie": config.get('cookie', ""),
        "User-Agent": config.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    }
    
    data = {
        "token": config['token'],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "action": "list_ex",
        "begin": "0",
        "count": str(per_page),
        "query": "",
        "fakeid": config['fakeid'],
        "type": "9"
    }

    page = int(math.ceil(total_count / per_page))
    content_list = []
    
    # Calculate cutoff time (7 days ago)
    cutoff_time = time.time() - 7 * 24 * 3600
    print(f"Fetching articles from the last 7 days (after {time.ctime(cutoff_time)})...")
    
    stop_scraping = False

    # Using tqdm for progress bar as shown in screenshot
    for i in tqdm(range(page), desc="获取文章列表"):
        if stop_scraping:
            break
            
        data["begin"] = str(i * per_page)
        
        try:
            response = requests.get(url, headers=headers, params=data, timeout=10)
            response.raise_for_status()
            content_json = response.json()
            
            base_resp = content_json.get('base_resp', {})
            if base_resp.get('ret') != 0:
                print(f"\nError from WeChat: {base_resp}")
                if base_resp.get('ret') == 200013:
                    print("Rate limit reached. Waiting 60s...")
                    time.sleep(60)
                elif base_resp.get('ret') == 200003:
                    print("Session invalid. Please update cookie/token.")
                    break
                
            if "app_msg_list" in content_json:
                for item in content_json["app_msg_list"]:
                    create_time = item.get('create_time')
                    # Check if article is older than cutoff
                    if create_time and create_time < cutoff_time:
                        print(f"\nReached article from {time.ctime(create_time)}. Stopping.")
                        stop_scraping = True
                        break
                    
                    # Filter for tender info (simple keyword check in title)
                    title = item.get('title', '')
                    # Keywords: 招标, 采购, 询价, 谈判, 磋商, 竞价
                    if any(kw in title for kw in ['招标', '采购', '询价', '谈判', '磋商', '竞价']):
                        link = item.get('link')
                        if link:
                            # Fetch details
                            detail = get_article_detail(link, config)
                            if detail:
                                item.update(detail)
                                # If project name wasn't found in text, use title
                                if item['project_name'] == "N/A":
                                    item['project_name'] = title
                        content_list.append(item)
                    else:
                        # Skip non-tender articles or just don't add them to the list?
                        # User said "Only get tender information".
                        pass
            
            # Save to JSON incrementally
            with open("content_list.json", "w", encoding="utf-8") as f:
                json.dump(content_list, f, ensure_ascii=False, indent=4)
            
            if stop_scraping:
                break

            # Sleep as per screenshot (random 5-10s)
            time.sleep(random.randint(5, 10))
                
        except Exception as e:
            print(f"\nError fetching page {i}: {e}")
            time.sleep(5)

    print(f"\nScraping complete. Saved {len(content_list)} tender articles to content_list.json.")

def get_total_count(config):
    """Helper to get the total number of articles to initialize the loop."""
    url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
    headers = {
        "Cookie": config.get('cookie', ""),
        "User-Agent": config.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    }
    data = {
        "token": config['token'],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "action": "list_ex",
        "begin": "0",
        "count": "5",
        "query": "",
        "fakeid": config['fakeid'],
        "type": "9"
    }
    
    try:
        response = requests.get(url, headers=headers, params=data, timeout=10)
        res_json = response.json()
        if res_json.get('base_resp', {}).get('ret') == 0:
            return int(res_json.get('app_msg_cnt', 0))
        else:
            print(f"Error getting count: {res_json}")
            return 0
    except Exception as e:
        print(f"Error getting count: {e}")
        return 0

def main():
    config = load_config()
    if not config:
        return

    if config['token'] == "REPLACE_WITH_YOUR_TOKEN" or "REPLACE_WITH_YOUR_FULL_COOKIE_STRING" in config['cookie']:
        print("Please update config.json with your actual cookie, token, and fakeid.")
        return

    print("Fetching total article count...")
    total_count = get_total_count(config)
    
    if total_count > 0:
        print(f"Total articles: {total_count}")
        get_content_list(total_count, config)
    else:
        print("Could not retrieve article count or count is 0.")

if __name__ == "__main__":
    main()
