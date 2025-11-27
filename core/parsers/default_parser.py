import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from core.parsers.base import BaseParser
from core.bid_record import BidInfo
from utils.logger import setup_logger

class DefaultParser(BaseParser):
    """
    Extracts structured bid information from article text using regex patterns.
    This is the original extraction logic moved to a parser class.
    """

    _LABELS: Tuple[str, ...] = ("项目名称", "预算金额", "采购人", "获取采购文件", "项目编号", "服务期限", "采购内容")

    def __init__(self, logger=None) -> None:
        self.logger = logger or setup_logger(self.__class__.__name__)
        pattern_config = {
            "project_name": self._build_pattern("项目名称"),
            "budget": self._build_pattern("预算金额"),
            "purchaser": self._build_pattern("采购人"),
            "doc_time": self._build_pattern("获取采购文件"),
            "project_number": self._build_pattern("项目编号", r"[A-Za-z0-9\-]+"),
            "service_period": self._build_pattern("服务期限"),
            "content": self._build_pattern("采购内容"),
        }
        flags = re.IGNORECASE | re.DOTALL
        self.patterns: Dict[str, re.Pattern[str]] = {
            field: re.compile(pattern, flags)
            for field, pattern in pattern_config.items()
        }
        self.project_split_pattern = re.compile(r"(?P<index>\d+)\s*项目名称")
        self.required_fields = ("project_name", "budget", "purchaser", "doc_time")

    def extract(self, text: str, article_meta: Mapping[str, Any]) -> List[Dict[str, str]]:
        """
        Parse article text and return a list of bid dictionaries.
        """
        if not text:
            self.logger.warning("Empty text received for extraction.")
            return []

        metadata = article_meta or {}
        project_blocks = self._split_projects(text)
        self.logger.info("Found %d project blocks in article.", len(project_blocks))
        bids: List[Dict[str, str]] = []

        for index, block in enumerate(project_blocks, start=1):
            normalized_block = block.strip()
            fields = {field: self._extract_field(pattern, normalized_block) for field, pattern in self.patterns.items()}

            if not self._validate_required_fields(fields):
                self.logger.warning("Skipping block #%d due to missing required fields.", index)
                continue

            bid = BidInfo(
                id=self._generate_id(fields["project_name"], fields["purchaser"]),
                project_name=fields["project_name"],
                budget=fields["budget"],
                purchaser=fields["purchaser"],
                doc_time=fields["doc_time"],
                project_number=fields["project_number"],
                service_period=fields["service_period"],
                content=fields["content"],
                source_url=str(metadata.get("url", "")),
                source_title=str(metadata.get("title", "")),
                extracted_time=self._timestamp(),
            )
            bids.append(bid.to_dict())

        self.logger.info("Successfully extracted %d bid(s).", len(bids))
        return bids

    def _split_projects(self, text: str) -> List[str]:
        """Split article text into project-sized chunks."""
        matches = list(self.project_split_pattern.finditer(text))
        if not matches:
            return [text] if "项目名称" in text else []

        blocks: List[str] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            blocks.append(text[start:end])

        return blocks

    def _extract_field(self, pattern: re.Pattern[str], text: str) -> str:
        """Run a regex pattern and return the first capture group."""
        match = pattern.search(text)
        if not match:
            return ""
        return match.group(1).strip()

    def _validate_required_fields(self, fields: Mapping[str, str]) -> bool:
        """Ensure required fields are present and formatted correctly."""
        if not all(fields.get(field, "").strip() for field in self.required_fields):
            return False

        budget = fields["budget"]
        if "元" not in budget:
            return False

        if len(fields["project_name"]) < 5:
            return False

        return True

    @staticmethod
    def _generate_id(project_name: str, purchaser: str) -> str:
        """Generate deterministic unique ID for each bid."""
        unique_key = f"{project_name}-{purchaser}"
        digest = hashlib.md5(unique_key.encode("utf-8")).hexdigest()
        return digest[:16]

    @staticmethod
    def _timestamp() -> str:
        """Return ISO 8601 timestamp with UTC timezone."""
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _build_pattern(cls, label: str, value_pattern: str = ".+?") -> str:
        """Create a regex that captures text until the next label or end of block."""
        boundaries = "|".join(l for l in cls._LABELS if l != label)
        return rf"{label}[:：\s]*({value_pattern})(?=\s*(?:{boundaries}|\Z))"
