import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["BIBCARD_DB"] = _tmp.name

import app as app_module  # noqa: E402

CARD = {
    "title": "自己調整学習の研究動向",
    "authors": "山田太郎",
    "year": "2024",
    "source": "教育工学雑誌",
    "keywords": "自己調整学習, メタ認知",
    "memo": "第3章が参考になる",
}


class BibCardTest(unittest.TestCase):
    def setUp(self):
        app_module.init_db()
        self.client = app_module.app.test_client()
        with app_module.app.app_context():
            conn = app_module.get_db()
            conn.execute("DELETE FROM cards")
            conn.commit()

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_index_ok(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("文献カード検索", res.get_data(as_text=True))

    def test_add_visible_delete_gone(self):
        res = self.client.post("/add", data=CARD)
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("自己調整学習の研究動向", body)
        self.assertIn("山田太郎", body)
        with app_module.app.app_context():
            conn = app_module.get_db()
            cid = conn.execute("SELECT id FROM cards").fetchone()["id"]
        res = self.client.post(f"/delete/{cid}")
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("自己調整学習の研究動向", body)

    def test_search_matches_title_authors_keywords(self):
        self.client.post("/add", data=CARD)
        self.client.post("/add", data={"title": "別の論文", "authors": "佐藤花子",
                                       "year": "2023", "source": "", "keywords": "認知負荷", "memo": ""})
        body = self.client.get("/?q=メタ認知").get_data(as_text=True)
        self.assertIn("自己調整学習の研究動向", body)
        self.assertNotIn("別の論文", body)
        body = self.client.get("/?q=佐藤").get_data(as_text=True)
        self.assertIn("別の論文", body)
        self.assertNotIn("自己調整学習の研究動向", body)
        body = self.client.get("/?q=存在しない語").get_data(as_text=True)
        self.assertNotIn("別の論文", body)
        self.assertNotIn("自己調整学習の研究動向", body)

    def test_empty_title_rejected(self):
        self.client.post("/add", data={"title": "  ", "authors": "誰か"})
        with app_module.app.app_context():
            conn = app_module.get_db()
            n = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
