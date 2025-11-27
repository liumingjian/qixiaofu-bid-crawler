from dataclasses import asdict, dataclass
from typing import Dict

@dataclass
class BidInfo:
    """Structured representation of a single bid announcement."""

    id: str
    project_name: str
    budget: str
    purchaser: str
    doc_time: str
    project_number: str = ""
    service_period: str = ""
    content: str = ""
    source_url: str = ""
    source_title: str = ""
    extracted_time: str = ""
    status: str = "new"

    def to_dict(self) -> Dict[str, str]:
        """Serialize dataclass to a plain dict."""
        return asdict(self)
