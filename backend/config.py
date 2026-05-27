import json
import os
from pathlib import Path
from typing import Optional, Literal

DB_PATH = Path(__file__).parent / "stock_analysis.db"
CONFIG_PATH = Path(__file__).parent / "config.json"

AdjustType = Literal["none", "forward", "backward"]


class ProviderConfig:
    def __init__(self):
        self.priority: list[str] = ["baostock", "efinance", "ths_http", "ths_sdk", "sina", "akshare"]
        self.ths_http_token: str = ""
        self.ths_http_refresh_token: str = ""
        self.ths_sdk_enabled: bool = False
        self.default_adjust: AdjustType = "forward"
        self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.priority = data.get("priority", self.priority)
                self.ths_http_token = data.get("ths_http_token", "")
                self.ths_http_refresh_token = data.get("ths_http_refresh_token", "")
                self.ths_sdk_enabled = data.get("ths_sdk_enabled", False)
                self.default_adjust = data.get("default_adjust", self.default_adjust)
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self):
        data = {
            "priority": self.priority,
            "ths_http_token": self.ths_http_token,
            "ths_http_refresh_token": self.ths_http_refresh_token,
            "ths_sdk_enabled": self.ths_sdk_enabled,
            "default_adjust": self.default_adjust,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.save()


settings = ProviderConfig()
