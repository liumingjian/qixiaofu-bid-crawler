from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping

class BaseParser(ABC):
    """Abstract base class for bid info parsers."""

    @abstractmethod
    def extract(self, text: str, article_meta: Mapping[str, Any]) -> List[Dict[str, str]]:
        """
        Extract bid information from text.
        
        Args:
            text: The article content text.
            article_meta: Metadata about the article (url, title, etc).
            
        Returns:
            List of dictionaries containing extracted bid info.
        """
        pass
