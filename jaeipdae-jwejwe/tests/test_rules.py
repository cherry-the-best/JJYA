"""계획서 3.5절 테스트 설계 중 로직으로 확인할 수 있는 항목.

    python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data  # noqa: E402
import events  # noqa: E402
import items  # noqa: E402
from characters import Player  # noqa: E402
from game import GameManager  # noqa: E402
from storage import SaveManager  # noqa: E402


def new_game(branch="육군", job="전산", seed=1):
    g = GameManager(seed=seed, save_manager=SaveManager(tempfile.mkdtemp()), autosave=False)
    g.new_game(branch, job)
    return g


class RuleTests(unittest.TestCase):
    def test_t01_air_force_jobs(self):
        self.assertEqual(data.jobs_for("공군"), ["보병", "취사", "전산", "운전", "정비"])
        self.assertEqual(data.JOB_NAMES["보병"]["공군"], "기지 방호")

    def test_t03_t04_career(self):
        g = new_game(job="전산")
        g.player.stats.update(intel=88, hp=60, mental=60)
        self.assertEqual(g.career(), "개발자")
        g.player.stats.update(intel=60, hp=80, mental=60)
        self.assertIn(g.career(), data.COMMON_CAREERS["hp"])

    def test_t05_promotion(self):
        p = Player("육군", "전산")
        p.progress = 3 / 18
        self.assertTrue(p.update_rank())
        self.assertEqual(p.rank, "일병")

    def test_t06_px_locked_for_private(self):
        p = Player("육군", "전산")
        p.train_count = 2
        self.assertNotIn("PX", p.available_actions())

    def test_t07_train_rule(self):
        p = Player("육군", "전산")
        self.assertEqual(p.available_actions(), ["훈련"])
        p.train_count = 2
        self.assertIn("심부름", p.available_actions())

    def test_t08_fail_on_zero(self):
        g = new_game()
        g.player.stats.update(hp=0, mental=0)
        self.assertTrue(g._check_fail())
        self.assertEqual(g.ending, data.FAIL_ENDING)

    def test_t09_low_intel_gets_notice(self):
        g = new_game()
        g.player.stats["intel"] = 50
        endings = {g.judge_ending() for _ in range(50)}
        self.assertTrue(endings <= {data.FAIL_ENDING, *data.RARE_ENDINGS})

    def test_t11_inventory_full(self):
        p = Player("육군", "전산")
        p.inventory = ["캔커피"] * data.INVENTORY_SIZE
        self.assertFalse(items.add_item(p, "핫팩"))

    def test_t12_t13_save_and_broken_file(self):
        folder = tempfile.mkdtemp()
        saver = SaveManager(folder)
        g = GameManager(seed=3, save_manager=saver)
        g.new_game("공군", "정비")
        saver.save(g.to_dict())
        g2 = GameManager(save_manager=saver)
        self.assertTrue(g2.load_game())
        self.assertEqual(g2.player.job, "정비")
        with open(saver.save_path, "w", encoding="utf-8") as f:
            f.write("{broken")
        self.assertIsNone(saver.load())

    def test_t14_npc_threads(self):
        g = new_game()
        for _ in range(20):
            g.state = "npc"
            g.start_npc_turn()
            self.assertTrue(g.poll_npc_turn(block=True))
            if g.state == "ending":
                break

    def test_t16_job_bonus(self):
        p = Player("육군", "전산")
        self.assertEqual(p.stats, {"hp": 70, "intel": 50, "mental": 70, "grudge": 0})

    def test_t19_branch_event_fail_grudge(self):
        p = Player("해병대", "보병")
        p.stats["hp"] = 35
        self.assertEqual(events.fail_grudge(p, "hp"), 20)

    def test_call_probability(self):
        self.assertEqual(events.call_probability("병장", 100), 0.0)
        self.assertAlmostEqual(events.call_probability("이병", 1000), 0.9)


if __name__ == "__main__":
    unittest.main()
