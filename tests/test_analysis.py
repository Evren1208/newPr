import unittest

from app.analysis_service import compare_exams, score_distribution, subject_stats
from app.models import ExamData, StudentRecord


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.current = ExamData(
            students=[
                StudentRecord("张三", {"语文": 80, "数学": 90}),
                StudentRecord("李四", {"语文": 60, "数学": 70}),
            ],
            subjects=["语文", "数学"],
            source_file="current.xlsx",
        )
        self.previous = ExamData(
            students=[
                StudentRecord("张三", {"语文": 70, "数学": 80}),
                StudentRecord("李四", {"语文": 65, "数学": 75}),
            ],
            subjects=["语文", "数学"],
            source_file="previous.xlsx",
        )

    def test_subject_stats(self):
        stats = {x.subject: x for x in subject_stats(self.current)}
        self.assertAlmostEqual(stats["语文"].mean, 70)
        self.assertAlmostEqual(stats["数学"].mean, 80)

    def test_compare(self):
        changes = compare_exams(self.current, self.previous)
        self.assertEqual(changes[0].name, "张三")
        self.assertEqual(changes[0].delta, 20)

    def test_distribution(self):
        dist = score_distribution(self.current)
        self.assertEqual(sum(dist.values()), 2)


if __name__ == "__main__":
    unittest.main()
