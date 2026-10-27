from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import requests

from .analysis_service import rule_based_summary
from .models import ExamData


class AiProvider(ABC):
    @abstractmethod
    def generate_class_summary(self, facts: Dict) -> str:
        raise NotImplementedError


class OpenAICompatibleProvider(AiProvider):
    """Generic provider for OpenAI-compatible APIs such as Qwen/DeepSeek gateways."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 45):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate_class_summary(self, facts: Dict) -> str:
        prompt = (
            "你是班主任家长会材料助手。请根据下面的匿名化班级统计数据，写一段220字以内、"
            "客观克制、不公开学生个人成绩和排名的班级情况总结。必须只使用给定事实，不要编造。\n\n"
            + json.dumps(facts, ensure_ascii=False)
        )
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你擅长把结构化教育统计数据整理成清晰、稳妥的中文总结。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class OfflineTemplateProvider(AiProvider):
    def __init__(self, exam: ExamData, previous: Optional[ExamData] = None):
        self.exam = exam
        self.previous = previous

    def generate_class_summary(self, facts: Dict) -> str:
        summary = rule_based_summary(self.exam, self.previous)
        return summary["highlights"] + summary["concerns"] + summary["suggestions"]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_ai_config() -> Dict:
    env_key = os.getenv("TEACHER_AI_API_KEY", "").strip()
    if env_key:
        return {
            "enabled": True,
            "base_url": os.getenv("TEACHER_AI_BASE_URL", "").strip(),
            "api_key": env_key,
            "model": os.getenv("TEACHER_AI_MODEL", "").strip(),
        }

    cfg = _project_root() / "config" / "ai.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            return {"enabled": False}
    return {"enabled": False}


def build_provider(current: ExamData, previous: Optional[ExamData] = None) -> AiProvider:
    cfg = load_ai_config()
    if cfg.get("enabled"):
        base_url = str(cfg.get("base_url") or "").strip()
        api_key = str(cfg.get("api_key") or "").strip()
        model = str(cfg.get("model") or "").strip()
        if base_url and api_key and model:
            return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    return OfflineTemplateProvider(current, previous)
