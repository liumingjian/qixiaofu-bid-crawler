import hashlib
import re
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from utils.logger import setup_logger


from core.bid_record import BidInfo


class BidInfoExtractor:
    """
    Extracts structured bid information from article text.
    Delegates to specific parsers based on the source account.
    """

    def __init__(self, logger=None) -> None:
        self.logger = logger or setup_logger(self.__class__.__name__)
        
        # Import here to avoid circular dependencies if any
        from core.parsers.default_parser import DefaultParser
        from core.parsers.dadanwang_parser import DaDanWangParser
        
        self.default_parser = DefaultParser(logger=self.logger)
        self.parsers: Dict[str, Any] = {
            "default": self.default_parser,
            "大单网": DaDanWangParser(logger=self.logger),
        }

    def extract_from_text(
        self,
        text: str,
        article_meta: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Parse article text and return a list of bid dictionaries.
        """
        if not text:
            self.logger.warning("Empty text received for extraction.")
            return []

        metadata = article_meta or {}
        source_name = metadata.get("source_account_name", "default")
        
        parser = self.parsers.get(source_name, self.default_parser)
        self.logger.info(f"Using parser '{parser.__class__.__name__}' for source '{source_name}'")
        
        return parser.extract(text, metadata)


