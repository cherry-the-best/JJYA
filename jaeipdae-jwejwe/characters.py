"""플레이어, NPC, Utility AI."""

import random

import data


class Character:
    def __init__(self, name, rank):
        self.name = name
        self.rank = rank

    def describe(self):
        return f"{self.rank} {self.name}"


class Player(Character):
    def __init__(self, branch, job, name="신병"):
        super().__init__(name, "이병")
        self.branch = branch
        self.job = job
        self.stats = dict(data.START_STATS)
        for stat, value in data.JOB_BONUS[job].items():
            self.stats[stat] += value
        self.progress = 0.0      # 0.0 ~ 1.0
        self.train_count = 0     # 연속 훈련 횟수
        self.inventory = []      # 최대 data.INVENTORY_SIZE
        self.accepted_nco = False
        self.hidden_bonus = 0.0

    @property
    def main_stat(self):
        """보직 주 스탯. 보정이 둘로 나뉜 보직은 둘 중 낮은 쪽."""
        bonus = data.JOB_BONUS[self.job]
        return min(bonus, key=lambda s: self.stats[s])

    def change_stat(self, stat, delta):
        self.stats[stat] = max(data.STAT_MIN, min(data.STAT_MAX, self.stats[stat] + delta))

    def apply(self, changes):
        for stat, delta in changes.items():
            self.change_stat(stat, delta)

    def update_rank(self):
        """진행률에 맞게 계급을 바꾸고, 바뀌었으면 True."""
        new_rank = self.rank
        for start, rank in data.RANKS:
            if self.progress >= start - 1e-9:
                new_rank = rank
        changed = new_rank != self.rank
        self.rank = new_rank
        return changed

    def available_actions(self):
        actions = []
        for rank in ["이병", "일병", "상병", "병장"]:
            actions += data.UNLOCKS[rank]
            if rank == self.rank:
                break
        if self.train_count < data.TRAIN_BEFORE_FREE:
            return ["훈련"]
        return actions

    def to_dict(self):
        return {
            "branch": self.branch, "job": self.job, "rank": self.rank,
            "stats": self.stats, "progress": self.progress,
            "train_count": self.train_count, "inventory": self.inventory,
            "accepted_nco": self.accepted_nco, "hidden_bonus": self.hidden_bonus,
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d["branch"], d["job"])
        p.rank = d["rank"]
        p.stats = dict(d["stats"])
        p.progress = d["progress"]
        p.train_count = d["train_count"]
        p.inventory = list(d["inventory"])
        p.accepted_nco = d["accepted_nco"]
        p.hidden_bonus = d["hidden_bonus"]
        return p


class UtilityAI:
    """행동마다 점수를 매기고, 상위 행동 중 점수 비례 확률로 하나를 고른다."""

    WEIGHTS = {"personality": 1.0, "affinity": 0.6, "rank_gap": 0.4, "mood": 0.3}
    TOP_N = 3

    def score(self, npc, action, ctx):
        affinity = npc.affinity / 100
        friendly = action in ("챙겨주기", "대화")
        affinity_term = affinity if friendly else 1 - affinity
        # 플레이어 계급이 낮을수록 갈구기, 심부름 점수가 높다
        rank_order = ["이병", "일병", "상병", "병장"].index(ctx["player_rank"])
        low_rank = 1 - rank_order / 3
        rank_term = low_rank if action in ("갈구기", "심부름") else 0.5
        mood_term = npc.mood / 100 if friendly else 1 - npc.mood / 100
        w = self.WEIGHTS
        return (w["personality"] * npc.personality[action]
                + w["affinity"] * affinity_term
                + w["rank_gap"] * rank_term
                + w["mood"] * mood_term)

    def choose(self, npc, ctx, rng):
        scored = sorted(((self.score(npc, a, ctx), a) for a in npc.personality), reverse=True)
        top = scored[: self.TOP_N]
        total = sum(s for s, _ in top)
        pick = rng.uniform(0, total)
        for s, action in top:
            pick -= s
            if pick <= 0:
                return action
        return top[0][1]


class NPC(Character):
    ai = UtilityAI()

    def __init__(self, npc_id, name, rank, personality):
        super().__init__(name, rank)
        self.id = npc_id
        self.personality = personality
        self.affinity = 50
        self.mood = 50

    def decide(self, ctx, seed):
        """ctx는 게임 상태의 복사본. 스레드에서 호출되므로 자기 상태만 읽는다."""
        rng = random.Random(seed)
        return self.ai.choose(self, ctx, rng)


def make_npcs():
    return [NPC(n["id"], n["name"], n["rank"], n["personality"]) for n in data.NPCS]
