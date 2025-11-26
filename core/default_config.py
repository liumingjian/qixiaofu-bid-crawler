from __future__ import annotations

from copy import deepcopy

DEFAULT_CONFIG = {
    "wechat": {
        "account_name": "",
        "max_articles_per_crawl": 50,
        "fakeid": "",
        "token": "",
        "cookie": "",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "page_size": 5,
        "days_limit": 7,
        "keyword_filters": ["招标", "采购", "询价", "谈判", "磋商", "竞价"],
        "request_interval_range": [5, 10],
        "request_timeout": 10,
        "retry_count": 3,
        "retry_delay": 5,
        "rate_limit_wait": 60,
        "fetch_rule": {"mode": "recent_days", "value": 7},
    },
    "email": {
        "smtp_server": "",
        "smtp_port": 465,
        "sender_email": "",
        "sender_password": "",
        "recipient_emails": [],
    },
    "scheduler": {
        "enabled": False,
        "cron": "0 7 * * *",
        "interval_minutes": None,
        "timezone": "Asia/Shanghai",
    },
    "scraper": {
        "headless": True,
        "wait_time": 5,
        "retry_count": 3,
        "retry_delay": 5,
        "random_delay_range": [2, 5],
    },
    "paths": {
        "data_dir": "data",
        "log_dir": "data/logs",
    },
    "logging": {"level": "INFO"},
}


def default_config_copy() -> dict:
    return deepcopy(DEFAULT_CONFIG)
