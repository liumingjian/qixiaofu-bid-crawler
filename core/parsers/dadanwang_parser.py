import re
from typing import Any, Dict, List, Mapping

from core.parsers.base import BaseParser
from core.bid_record import BidInfo
from utils.logger import setup_logger
from datetime import datetime, timezone
import hashlib

class DaDanWangParser(BaseParser):
    """
    Parser specifically for '大单网' articles.
    """

    def __init__(self, logger=None) -> None:
        self.logger = logger or setup_logger(self.__class__.__name__)
        # Regex patterns for DaDanWang format
        # Use a list of known labels to stop capturing
        self.labels = ["项目名称", "预算金额", "单位名称", "采购目标", "采购要求", "预计采购时间", "云头条声明"]
        label_pattern = "|".join(self.labels)
        
        self.patterns = {
            "project_name": re.compile(rf"项目名称[:：\s]*(.*?)(?={label_pattern}|$)"),
            "budget": re.compile(rf"预算金额[:：\s]*(.*?)(?={label_pattern}|$)"),
            "purchaser": re.compile(rf"单位名称[:：\s]*(.*?)(?={label_pattern}|$)"),
            "doc_time": re.compile(rf"预计采购时间[:：\s]*(.*?)(?={label_pattern}|$)"),
            "content": re.compile(rf"采购目标[:：\s]*(.*?)(?={label_pattern}|$)"),
        }
        
        # Keywords that indicate a winning bid (result) rather than a tender
        self.winning_keywords = ["中标", "成交", "结果", "赢家", "第一名", "候选人"]

    def extract(self, text: str, article_meta: Mapping[str, Any]) -> List[Dict[str, str]]:
        if not text:
            return []

        title = article_meta.get("title", "")
        
        # 1. Filter out winning bids based on title
        if any(kw in title for kw in self.winning_keywords):
            self.logger.info(f"Skipping article '{title}' as it appears to be a winning bid result.")
            return []

        # 2. Extract fields
        fields = {}
        # Try standard labeled format first
        for key, pattern in self.patterns.items():
            match = pattern.search(text)
            if match:
                fields[key] = match.group(1).strip()
            else:
                fields[key] = ""

        # 3. Fallback for short format (e.g., Sample 02)
        # "2025 年... 公司发布《项目名》招标公告，预算 123 元。"
        if not fields["project_name"]:
            proj_match = re.search(r"《(.*?)》", text)
            if proj_match:
                fields["project_name"] = proj_match.group(1).strip()
        
        if not fields["purchaser"]:
            # Look for text before "发布"
            purchaser_match = re.search(r"([\u4e00-\u9fa5]+公司|[\u4e00-\u9fa5]+局)发布", text)
            if purchaser_match:
                fields["purchaser"] = purchaser_match.group(1).strip()
            else:
                 # Try to grab the subject at the start
                 purchaser_match = re.search(r"，(.*?)(?=发布)", text)
                 if purchaser_match:
                     fields["purchaser"] = purchaser_match.group(1).strip()

        if not fields["budget"]:
            budget_match = re.search(r"预算[:：\s]*([\d\.]+\s*[万亿]?元?)", text)
            if budget_match:
                fields["budget"] = budget_match.group(1).strip()

        # 4. Validate required fields
        # DaDanWang samples show "单位名称" (purchaser), "项目名称", "预算金额".
        # "获取采购文件" (doc_time) might be missing or labeled as "预计采购时间".
        if not fields["project_name"] or not fields["budget"]:
             self.logger.warning(f"Skipping article '{title}' due to missing project_name or budget.")
             return []

        # 4. Construct BidInfo
        bid = BidInfo(
            id=self._generate_id(fields["project_name"], fields["purchaser"]),
            project_name=fields["project_name"],
            budget=fields["budget"],
            purchaser=fields["purchaser"],
            doc_time=fields["doc_time"] or datetime.now().strftime("%Y-%m-%d"), # Fallback if missing
            project_number="",
            service_period="",
            content=fields["content"],
            source_url=str(article_meta.get("url", "")),
            source_title=str(title),
            extracted_time=self._timestamp(),
        )

        return [bid.to_dict()]

    @staticmethod
    def _generate_id(project_name: str, purchaser: str) -> str:
        unique_key = f"{project_name}-{purchaser}"
        digest = hashlib.md5(unique_key.encode("utf-8")).hexdigest()
        return digest[:16]

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
