"""Configuration migration utilities for backward compatibility."""

from __future__ import annotations

from typing import Any, Dict
import re


def migrate_to_v2(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old single-account config to multi-account format.
    
    Old format:
        {"wechat": {"fakeid": "...", "token": "...", ...}}
    
    New format:
        {"wechat": {"accounts": [{"id": "...", "name": "...", ...}]}}
    """
    if not config:
        return config
    
    wechat = config.get("wechat", {})
    
    # Check if already migrated
    if "accounts" in wechat:
        return config
    
    # Migrate single account to accounts array
    if wechat.get("fakeid") or wechat.get("token"):
        account_name = wechat.get("account_name", "默认账号")
        account_id = _generate_account_id(account_name)
        
        account = {
            "id": account_id,
            "name": account_name,
            "fakeid": wechat.get("fakeid", ""),
            "token": wechat.get("token", ""),
            "cookie": wechat.get("cookie", ""),
            "page_size": wechat.get("page_size", 5),
            "days_limit": wechat.get("days_limit", 7),
            "enabled": True
        }
        
        # Create new wechat config with accounts array
        new_wechat = {
            "accounts": [account],
            "keyword_filters": wechat.get("keyword_filters", ["招标", "采购"]),
            "request_interval_range": wechat.get("request_interval_range", [5, 10]),
            "request_timeout": wechat.get("request_timeout", 10),
            "retry_count": wechat.get("retry_count", 3),
            "retry_delay": wechat.get("retry_delay", 5),
            "rate_limit_wait": wechat.get("rate_limit_wait", 60),
            "user_agent": wechat.get("user_agent", "")
        }
        
        # Preserve other fields that may exist
        for key, value in wechat.items():
            if key not in ["fakeid", "token", "cookie", "account_name", "page_size", "days_limit"] and key not in new_wechat:
                new_wechat[key] = value
        
        config["wechat"] = new_wechat
    
    # Add bid_sites if not present
    if "bid_sites" not in config:
        config["bid_sites"] = []
    
    return config


def _generate_account_id(name: str) -> str:
    """Generate a URL-safe ID from account name."""
    # Remove non-alphanumeric characters and convert to lowercase
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    
    # If empty or starts with number, prefix with 'account'
    if not slug or slug[0].isdigit():
        slug = f"account-{slug}" if slug else "default"
    
    return slug[:50]  # Limit length
