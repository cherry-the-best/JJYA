"""밸런스 자동 플레이. 화면 없이 군별로 N판을 돌려 엔딩 분포를 본다.

    python tests/simulate.py          # 군별 100판
    python tests/simulate.py 500      # 군별 500판
"""

import collections
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data  # noqa: E402
from game import GameManager  # noqa: E402
from storage import SaveManager  # noqa: E402


def play_once(branch, seed, saver):
    rng = random.Random(seed)
    game = GameManager(seed=seed, save_manager=saver, autosave=False)
    game.new_game(branch, rng.choice(data.jobs_for(branch)))
    for _ in range(10000):
        scene = game.scene()
        state = scene["state"]
        if state == "ending":
            return game
        if state == "minigame":
            game.finish_minigame(rng.choice(["상", "중", "중", "하"]))
        elif state == "npc":
            game.start_npc_turn()
            game.poll_npc_turn(block=True)
        else:
            game.choose(rng.choice(scene["options"])[0])
    raise RuntimeError("게임이 끝나지 않는다")


def main(runs=100):
    saver = SaveManager(tempfile.mkdtemp())
    for branch in data.BRANCHES:
        endings = collections.Counter()
        cycles = []
        for i in range(runs):
            game = play_once(branch, i, saver)
            endings[game.ending] += 1
            cycles.append(game.cycle)
        fail = endings[data.FAIL_ENDING]
        print(f"\n[{branch}] {runs}판, 평균 {sum(cycles) / runs:.1f}사이클, "
              f"입영통지서 {fail}판 ({fail / runs:.0%})")
        for name, count in endings.most_common():
            print(f"  {name:<16} {count}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
