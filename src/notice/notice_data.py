from dataclasses import dataclass
from typing import Optional


@dataclass
class Notice:
    """公告数据类"""
    id: str
    enabled: bool = True
    title: str = ""
    content: str = ""
    link: Optional[str] = None
    timestamp: str = ""  # ← 添加这一行

    @classmethod
    def from_dict(cls, data: dict) -> "Notice":
        return cls(
            id=data.get("id", ""),
            enabled=data.get("enabled", True),
            title=data.get("title", ""),
            content=data.get("content", ""),
            link=data.get("link", None),
            timestamp=data.get("timestamp", ""),  # ← 添加这一行
        )

    def is_valid(self) -> bool:
        return self.enabled and bool(self.id) and bool(self.title) and bool(self.content)