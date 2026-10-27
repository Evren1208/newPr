from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StudentRecord:
    name: str
    scores: Dict[str, float]
    student_id: Optional[str] = None
    class_name: Optional[str] = None

    @property
    def total(self) -> float:
        return float(sum(self.scores.values()))

    @property
    def average(self) -> float:
        return self.total / len(self.scores) if self.scores else 0.0


@dataclass
class ExamData:
    students: List[StudentRecord]
    subjects: List[str]
    source_file: str
    exam_name: str = "本次考试"
    header_row: int = 1
    warnings: List[str] = field(default_factory=list)


@dataclass
class SubjectStats:
    subject: str
    mean: float
    median: float
    max_score: float
    min_score: float
    pass_rate: float
    excellent_rate: float


@dataclass
class StudentChange:
    name: str
    current_total: float
    previous_total: float
    delta: float
    subject_deltas: Dict[str, float]


@dataclass
class MappingConfig:
    header_row: int
    name_col: int
    subject_cols: List[int]
    id_col: Optional[int] = None
    class_col: Optional[int] = None
