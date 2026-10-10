import unittest

from laboratorio_spark.scripts.report_helpers import (
    format_count,
    format_pct,
)


class ReportHelperTests(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(format_count(500000), "500 000")
        self.assertEqual(format_pct(0.1190814), "11,91 %")

if __name__ == "__main__":
    unittest.main()
