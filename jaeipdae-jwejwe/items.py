"""아이템과 PX."""

import data


def use_item(player, index):
    """보유한 아이템을 사용한다. 효과가 없는 아이템(면제권 등)은 게임 로직에서 따로 처리."""
    name = player.inventory.pop(index)
    player.apply(data.ITEMS.get(name, {}))
    return name


def add_item(player, name):
    """6칸이 차 있으면 False를 돌려주고, UI가 버릴 아이템을 묻는다."""
    if len(player.inventory) >= data.INVENTORY_SIZE:
        return False
    player.inventory.append(name)
    return True


def visit_px(player, rng):
    """계급별 확률로 아이템을 얻는다. 일병은 선임을 만나 정신력이 깎일 수 있다."""
    log = []
    if player.rank == "일병" and rng.random() < data.PX_SENIOR_RATE:
        player.change_stat("mental", -5)
        log.append("PX에서 선임과 마주쳤다. 정신력 -5")
    if rng.random() < data.PX_ITEM_RATE.get(player.rank, 0):
        name = rng.choice(list(data.ITEMS))
        if add_item(player, name):
            log.append(f"{name}을(를) 샀다.")
        else:
            log.append("관물대가 가득 차서 아무것도 못 샀다.")
    return log
