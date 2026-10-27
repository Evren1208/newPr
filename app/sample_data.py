from pathlib import Path
import random

from openpyxl import Workbook

SUBJECTS = ["语文", "数学", "英语", "物理", "化学"]
SURNAMES = ["张", "李", "王", "赵", "陈", "刘", "杨", "黄", "周", "吴", "徐", "孙"]
NAMES = ["子涵", "宇轩", "雨桐", "浩然", "梓萱", "思远", "若曦", "嘉怡", "俊杰", "晨曦", "一诺", "欣怡"]


def create_sample(path: str, seed: int = 42, shift: float = 0.0):
    random.seed(seed)
    wb = Workbook()
    ws = wb.active
    ws.title = "成绩"
    ws.append(["学号", "姓名", "班级"] + SUBJECTS + ["总分"])
    for i in range(1, 41):
        name = SURNAMES[(i - 1) % len(SURNAMES)] + NAMES[(i - 1) % len(NAMES)] + str((i - 1) // len(NAMES) + 1)
        scores = []
        for j, _ in enumerate(SUBJECTS):
            base = 72 + (j * 2) + shift
            v = max(35, min(100, random.gauss(base, 12)))
            scores.append(round(v, 1))
        ws.append([f"S{i:03d}", name, "高一3班"] + scores + [round(sum(scores), 1)])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
