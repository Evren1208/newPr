from __future__ import annotations

from statistics import mean, median
from typing import Dict, List, Optional

from .models import ExamData, StudentChange, SubjectStats


def _rate(values: List[float], threshold: float) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v >= threshold) / len(values) * 100.0


def subject_stats(exam: ExamData, pass_score: float = 60.0, excellent_score: float = 85.0) -> List[SubjectStats]:
    out: List[SubjectStats] = []
    for subject in exam.subjects:
        values = [s.scores[subject] for s in exam.students if subject in s.scores]
        if not values:
            continue
        out.append(SubjectStats(
            subject=subject,
            mean=mean(values),
            median=median(values),
            max_score=max(values),
            min_score=min(values),
            pass_rate=_rate(values, pass_score),
            excellent_rate=_rate(values, excellent_score),
        ))
    return out


def class_overview(exam: ExamData) -> Dict[str, float]:
    totals = [s.total for s in exam.students]
    avgs = [s.average for s in exam.students]
    return {
        "student_count": float(len(exam.students)),
        "subject_count": float(len(exam.subjects)),
        "avg_total": mean(totals) if totals else 0.0,
        "median_total": median(totals) if totals else 0.0,
        "max_total": max(totals) if totals else 0.0,
        "min_total": min(totals) if totals else 0.0,
        "avg_subject_score": mean(avgs) if avgs else 0.0,
    }


def score_distribution(exam: ExamData) -> Dict[str, int]:
    bands = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "<60": 0}
    for s in exam.students:
        v = s.average
        if v >= 90:
            bands["90-100"] += 1
        elif v >= 80:
            bands["80-89"] += 1
        elif v >= 70:
            bands["70-79"] += 1
        elif v >= 60:
            bands["60-69"] += 1
        else:
            bands["<60"] += 1
    return bands


def compare_exams(current: ExamData, previous: Optional[ExamData]) -> List[StudentChange]:
    if previous is None:
        return []
    prev_map = {s.name: s for s in previous.students}
    changes: List[StudentChange] = []
    for cur in current.students:
        prev = prev_map.get(cur.name)
        if not prev:
            continue
        common = sorted(set(cur.scores) & set(prev.scores))
        subject_deltas = {sub: cur.scores[sub] - prev.scores[sub] for sub in common}
        changes.append(StudentChange(
            name=cur.name,
            current_total=cur.total,
            previous_total=prev.total,
            delta=cur.total - prev.total,
            subject_deltas=subject_deltas,
        ))
    changes.sort(key=lambda x: x.delta, reverse=True)
    return changes


def build_summary_facts(exam: ExamData, previous: Optional[ExamData] = None) -> Dict:
    stats = subject_stats(exam)
    overview = class_overview(exam)
    changes = compare_exams(exam, previous)
    return {
        "student_count": int(overview["student_count"]),
        "subject_count": int(overview["subject_count"]),
        "subjects": [
            {
                "name": s.subject,
                "mean": round(s.mean, 1),
                "pass_rate": round(s.pass_rate, 1),
                "excellent_rate": round(s.excellent_rate, 1),
            }
            for s in stats
        ],
        "matched_previous_students": len(changes),
        "improved_students": sum(1 for c in changes if c.delta > 0),
        "declined_students": sum(1 for c in changes if c.delta < 0),
    }


def rule_based_summary(exam: ExamData, previous: Optional[ExamData] = None) -> Dict[str, str]:
    stats = subject_stats(exam)
    if not stats:
        return {"highlights": "暂无可分析数据。", "concerns": "暂无可分析数据。", "suggestions": "请检查成绩表。"}

    strongest = max(stats, key=lambda x: x.mean)
    weakest = min(stats, key=lambda x: x.mean)
    high_pass = max(stats, key=lambda x: x.pass_rate)
    low_pass = min(stats, key=lambda x: x.pass_rate)

    highlights = (
        f"从本次成绩看，{strongest.subject}平均分相对较高（{strongest.mean:.1f}分），"
        f"{high_pass.subject}及格率表现较好（{high_pass.pass_rate:.1f}%）。"
    )
    concerns = (
        f"目前需要重点关注{weakest.subject}，该科平均分为{weakest.mean:.1f}分；"
        f"{low_pass.subject}及格率为{low_pass.pass_rate:.1f}%。"
    )

    if previous:
        changes = compare_exams(exam, previous)
        if changes:
            improved = sum(1 for c in changes if c.delta > 0)
            declined = sum(1 for c in changes if c.delta < 0)
            concerns += f"与上次考试相比，可匹配{len(changes)}名学生，其中{improved}人总分提升，{declined}人下降。"
        else:
            concerns += "未能匹配上次考试学生数据。"
    else:
        concerns += "当前未导入上次考试数据，暂不进行进退步比较。"

    suggestions = (
        f"下一阶段建议保持{strongest.subject}的学习节奏，同时围绕{weakest.subject}进行分层巩固；"
        "对临界学生设置短周期目标，并通过错题整理、基础知识复盘和阶段性反馈持续跟踪。"
    )
    return {"highlights": highlights, "concerns": concerns, "suggestions": suggestions}


def student_comment(name: str, current_scores: Dict[str, float], previous_scores: Optional[Dict[str, float]] = None) -> str:
    if not current_scores:
        return "暂无足够数据生成建议。"
    best = max(current_scores.items(), key=lambda kv: kv[1])
    weak = min(current_scores.items(), key=lambda kv: kv[1])
    parts = [f"{best[0]}表现相对较好（{best[1]:.0f}分），可继续保持当前学习节奏。"]
    if weak[1] < 80:
        parts.append(f"{weak[0]}目前相对薄弱（{weak[1]:.0f}分），建议优先复盘基础知识和典型错题。")
    if previous_scores:
        common = set(current_scores) & set(previous_scores)
        if common:
            deltas = {s: current_scores[s] - previous_scores[s] for s in common}
            up = max(deltas.items(), key=lambda kv: kv[1])
            down = min(deltas.items(), key=lambda kv: kv[1])
            if up[1] >= 5:
                parts.append(f"{up[0]}较上次提升{up[1]:.0f}分，进步较明显。")
            if down[1] <= -5:
                parts.append(f"{down[0]}较上次下降{abs(down[1]):.0f}分，需要关注近期学习状态。")
    return "".join(parts)
