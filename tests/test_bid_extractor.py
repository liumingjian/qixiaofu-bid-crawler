import json
import unittest
from pathlib import Path

from core.bid_extractor import BidInfoExtractor


class TestBidInfoExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        article_path = Path("wechat_article.json")
        with article_path.open("r", encoding="utf-8") as fp:
            cls.sample_article = json.load(fp)
        cls.sample_text = cls.sample_article["content_text"]

    def setUp(self) -> None:
        self.extractor = BidInfoExtractor()

    def test_split_projects_detects_all_blocks(self) -> None:
        blocks = self.extractor._split_projects(self.sample_text)
        self.assertEqual(4, len(blocks))
        for block in blocks:
            self.assertIn("项目名称", block)

    def test_extract_from_real_article(self) -> None:
        bids = self.extractor.extract_from_text(
            self.sample_text,
            {"url": "https://mp.weixin.qq.com/s/example", "title": self.sample_article["title"]},
        )
        self.assertEqual(4, len(bids))

        first = bids[0]
        self.assertIn("内蒙古科技大学", first["project_name"])
        self.assertIn("97.38", first["budget"])
        self.assertEqual("内蒙古科技大学数据中心IT机房专用精密空调采购项目（二次）", first["project_name"])
        self.assertIn("2025年11月24日－2025年12月1日", first["doc_time"])

        second = next(bid for bid in bids if "宿州学院" in bid["project_name"])
        self.assertIn("1年", second["service_period"])
        self.assertIn("SZXYSSJS-2025-8-C", second["project_number"])

        third = next(bid for bid in bids if "桂林银行" in bid["project_name"])
        self.assertEqual("GYJC2025129", third["project_number"])
        self.assertIn("oracle数据库", third["content"].lower())

        fourth = next(bid for bid in bids if "吕梁市财政局" in bid["project_name"])
        self.assertIn("34.900896万元", fourth["budget"])

        ids = [bid["id"] for bid in bids]
        self.assertEqual(len(ids), len(set(ids)))

    def test_missing_required_fields_are_skipped(self) -> None:
        text = "1项目名称：示例项目预算金额：10万元"  # 缺少采购人/获取文件时间
        bids = self.extractor.extract_from_text(text, {})
        self.assertEqual([], bids)


if __name__ == "__main__":
    unittest.main()
