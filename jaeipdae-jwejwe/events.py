"""이벤트 선택, 스탯 판정, 선임 집합 판정."""

import data


def call_probability(rank, grudge):
    """선임 집합 확률. 병장은 판정 대신 집합 걸기 선택지가 열린다."""
    if rank == "병장":
        return 0.0
    return min(0.9, data.CALL_BASE[rank] + data.CALL_K * grudge)


def check_success(player, check):
    """판정 스탯 / 100, 최소 10%에서 최대 90%."""
    if check == "hp_mental_min":
        value = min(player.stats["hp"], player.stats["mental"])
    else:
        value = player.stats[check]
    return max(0.1, min(0.9, value / 100))


def fail_grudge(player, check):
    """군별 이벤트 실패 시 찍힘도: 기본 5, 이병과 일병 +10, 판정 스탯 40 미만 +5."""
    amount = 5
    if player.rank in ("이병", "일병"):
        amount += 10
    value = (min(player.stats["hp"], player.stats["mental"])
             if check == "hp_mental_min" else player.stats[check])
    if value < 40:
        amount += 5
    return min(amount, 20)


class EventManager:
    def __init__(self, rng):
        self.rng = rng

    def pick_event(self, rank):
        pool = [e for e in data.EVENTS if rank in e["ranks"]]
        return self.rng.choice(pool) if pool else None

    def resolve(self, player, event, option_index):
        """선택지 결과를 적용하고 (문장, 변화량)을 돌려준다."""
        label, changes = event["options"][option_index]
        changes = dict(changes)
        if "check" in event and option_index == 0:
            if self.rng.random() >= check_success(player, event["check"]):
                changes["hp"] = changes.get("hp", 0) - 5
                changes["grudge"] = changes.get("grudge", 0) + 5
                label += " (실패)"
        player.apply(changes)
        return label, changes

    def resolve_branch_event(self, player, ev):
        """군별 고유 이벤트. 성공하면 포상, 실패하면 찍힘도 상승."""
        if self.rng.random() < check_success(player, ev["check"]):
            player.apply(ev["success"])
            player.hidden_bonus += ev.get("hidden_bonus", 0)
            if ev.get("item") and len(player.inventory) < data.INVENTORY_SIZE:
                player.inventory.append(ev["item"])
            return True, ev.get("leave", 0)
        changes = dict(ev["fail"])
        changes["grudge"] = changes.get("grudge", 0) + fail_grudge(player, ev["check"])
        player.apply(changes)
        return False, 0
