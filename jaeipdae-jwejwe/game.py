"""GameManager: 사이클 진행, 진급, 해금, 실패와 엔딩 판정.

이 파일은 tkinter를 전혀 모른다. 화면 없이도 돌아가야
tests/simulate.py로 자동 플레이 밸런스 테스트를 할 수 있다.

UI와의 약속
  UI -> 로직 : new_game(), load_game(), choose(option_id), finish_minigame(grade),
               start_npc_turn(), poll_npc_turn()
  로직 -> UI : scene()  지금 보여 줄 장면 하나를 dict로 돌려준다
"""

import collections
import copy
import queue
import random
import threading

import data
import events
import items
import minigames
from characters import Player, make_npcs
from storage import SaveManager

NPC_TIMEOUT = 1.0  # 초. 늦은 NPC는 '대기'로 처리


class GameManager:
    def __init__(self, seed=None, save_manager=None, autosave=True):
        self.rng = random.Random(seed)
        self.saver = save_manager or SaveManager()
        self.autosave = autosave
        self.events = events.EventManager(self.rng)
        self.player = None
        self.npcs = []
        self.state = "title"
        self.cycle = 0
        self.log = collections.deque(maxlen=200)
        self.pending_event = None
        self.minigame = None
        self.message = ""
        self.ending = None
        self.done_branch_events = []
        self.nco_offered = False
        self.result_queue = queue.Queue()
        self._threads = []

    # ------------------------------------------------------------ 시작
    def new_game(self, branch, job):
        if job not in data.jobs_for(branch):
            raise ValueError(f"{branch}에는 {job} 보직이 없다")
        self.player = Player(branch, job)
        self.npcs = make_npcs()
        self.cycle = 1
        self.log.clear()
        self._start_morning()

    def load_game(self):
        state = self.saver.load()
        if not state:
            return False
        self.player = Player.from_dict(state["player"])
        self.npcs = make_npcs()
        for npc in self.npcs:
            npc.affinity = state["affinity"].get(npc.id, 50)
        self.cycle = state["cycle"]
        self.done_branch_events = state["done_branch_events"]
        self.nco_offered = state["nco_offered"]
        self._start_morning()
        return True

    def to_dict(self):
        return {
            "player": self.player.to_dict(),
            "affinity": {n.id: n.affinity for n in self.npcs},
            "cycle": self.cycle,
            "done_branch_events": self.done_branch_events,
            "nco_offered": self.nco_offered,
        }

    @property
    def total_cycles(self):
        return data.BRANCHES[self.player.branch]["cycles"]

    # ------------------------------------------------------------ 장면
    def scene(self):
        p = self.player
        status = None
        if p:
            status = {"branch": p.branch, "job": data.JOB_NAMES[p.job][p.branch],
                      "rank": p.rank, "stats": dict(p.stats),
                      "progress": round(p.progress * 100, 1), "cycle": self.cycle,
                      "inventory": list(p.inventory)}
        options = []
        if self.state == "morning":
            options = [("next", "일과 시작")]
        elif self.state == "day":
            options = [(a, a) for a in p.available_actions()]
        elif self.state == "event":
            options = [(str(i), label) for i, (label, _) in enumerate(self.pending_event["options"])]
        elif self.state == "evening":
            options = [("개인정비", "개인정비"), ("청소", "청소"), ("독서", "독서")]
        elif self.state == "minigame":
            options = []  # UI가 미니게임 화면을 띄우고 finish_minigame()을 부른다
        return {"state": self.state, "text": self.message, "options": options,
                "status": status, "minigame": self.minigame.name if self.minigame else None,
                "ending": self.ending}

    def _say(self, text):
        self.message = text
        self.log.append(text)

    # ------------------------------------------------------------ 입력
    def choose(self, option_id):
        handler = {"morning": self._after_morning, "day": self._do_action,
                   "event": self._do_event, "evening": self._do_evening}.get(self.state)
        if handler is None:
            raise RuntimeError(f"{self.state} 상태에서는 선택할 수 없다")
        handler(option_id)

    def finish_minigame(self, grade):
        p = self.player
        p.change_stat(p.main_stat, data.MINIGAME_REWARD[grade])
        if grade == "하":
            p.change_stat("grudge", data.MINIGAME_FAIL_GRUDGE)
        p.apply(data.DELTAS["훈련"])
        p.train_count += 1
        self._say(f"{self.minigame.name} 결과: {grade}")
        self.minigame = None
        self._after_day()

    # ------------------------------------------------------------ 아침
    def _start_morning(self):
        self.state = "morning"
        p = self.player
        p.apply(data.DELTAS["아침"])
        kind = self.rng.choice(["실내점호", "실외점호와 뜀걸음"])
        text = f"{self.cycle}사이클 아침. {kind}."
        if self.rng.random() < data.MORNING_MISTAKE_RATE:
            p.apply(data.DELTAS["점호 실수"])
            text += " 점호 중에 실수를 했다. 찍힘도가 올랐다."
        self._say(text)

    def _after_morning(self, _):
        if not self._check_fail():
            self.state = "day"
            self._say("오늘 일과는 무엇을 할까?")

    # ------------------------------------------------------------ 일과
    def _do_action(self, action):
        p = self.player
        if action not in p.available_actions():
            raise ValueError(f"아직 고를 수 없는 행동: {action}")
        if action == "훈련":
            name = self.rng.choice(minigames.minigames_for(p.job))
            self.minigame = minigames.create(name, p.rank)
            self.state = "minigame"
            self._say(f"훈련: {name}")
            return
        p.train_count = 0
        p.apply(data.DELTAS[action])
        text = f"{action}을(를) 했다."
        if action == "PX":
            text += " " + " ".join(items.visit_px(p, self.rng))
        if action == "집합 걸기":
            for npc in self.npcs:
                if npc.rank == "후임":
                    npc.affinity = max(0, npc.affinity - 10)
        self._say(text)
        self._after_day()

    def _after_day(self):
        if self._check_fail():
            return
        p = self.player
        if p.rank == "상병" and not self.nco_offered and self.rng.random() < 0.2:
            self.nco_offered = True
            self.pending_event = {"id": "nco", "text": "행보관이 부사관 지원을 권한다.",
                                  "options": [("수락한다", {}), ("정중히 거절한다", {})]}
            self.state = "event"
            self._say(self.pending_event["text"])
            return
        if self.rng.random() < 0.35:
            ev = self.events.pick_event(p.rank)
            if ev:
                self.pending_event = ev
                self.state = "event"
                self._say(ev["text"])
                return
        self._start_evening()

    def _do_event(self, option_id):
        ev = self.pending_event
        idx = int(option_id)
        if ev["id"] == "nco":
            self.player.accepted_nco = idx == 0
            self._say("부사관 지원서를 냈다." if idx == 0 else "아직은 전역이 좋다.")
        else:
            label, _ = self.events.resolve(self.player, ev, idx)
            self._say(label)
        self.pending_event = None
        if not self._check_fail():
            self._start_evening()

    # ------------------------------------------------------------ 저녁
    def _start_evening(self):
        self.state = "evening"
        self._say("저녁 시간이다.")

    def _do_evening(self, option_id):
        p = self.player
        p.apply(data.DELTAS[option_id])
        if self.rng.random() < events.call_probability(p.rank, p.stats["grudge"]):
            if "집합 면제권" in p.inventory:
                p.inventory.remove("집합 면제권")
                self._say("집합이 걸렸지만 면제권을 썼다.")
            else:
                p.apply(data.DELTAS["집합 당함"])
                self._say("저녁 점호 후 선임 집합. 정신력이 깎였다.")
        else:
            self._say(f"{option_id}로 하루를 마쳤다.")
        if self._check_fail():
            return
        self.state = "npc"  # UI는 start_npc_turn() 후 poll_npc_turn()을 after()로 반복

    # ------------------------------------------------------------ NPC 병렬 처리
    def start_npc_turn(self):
        ctx = {"player_rank": self.player.rank, "stats": dict(self.player.stats)}
        self.result_queue = queue.Queue()
        self._threads = []
        for npc in self.npcs:
            seed = self.rng.random()
            npc_copy = copy.deepcopy(npc)  # 스레드는 복사본만 읽는다
            t = threading.Thread(target=self._npc_worker, args=(npc_copy, ctx, seed), daemon=True)
            t.start()
            self._threads.append(t)

    def _npc_worker(self, npc, ctx, seed):
        self.result_queue.put((npc.id, npc.decide(ctx, seed)))

    def poll_npc_turn(self, block=False):
        """결과가 다 모였으면 반영하고 True. block=True면 기다린다(테스트용)."""
        if block:
            for t in self._threads:
                t.join(NPC_TIMEOUT)
        elif any(t.is_alive() for t in self._threads):
            return False
        results = {}
        while not self.result_queue.empty():
            npc_id, action = self.result_queue.get()
            results[npc_id] = action
        lines = []
        for npc in self.npcs:  # 출력 순서를 NPC 순서로 고정해 재현 가능하게
            action = results.get(npc.id, "무시")
            self.player.apply(data.NPC_ACTION_EFFECTS[action])
            npc.affinity = max(0, min(100, npc.affinity + (2 if action in ("챙겨주기", "대화") else -1)))
            lines.append(data.NPC_ACTION_LINES[action].format(name=npc.name))
        self._say("\n".join(lines))
        self._end_cycle()
        return True

    # ------------------------------------------------------------ 사이클 끝
    def _end_cycle(self):
        if self._check_fail():
            return
        p = self.player
        p.progress = min(1.0, p.progress + 1 / self.total_cycles)
        if p.update_rank():
            self.log.append(f"{p.rank}(으)로 진급했다.")
        for ev in data.BRANCH_EVENTS[p.branch]:
            if ev["name"] not in self.done_branch_events and ev["rank"] == p.rank:
                self.done_branch_events.append(ev["name"])
                ok, leave = self.events.resolve_branch_event(p, ev)
                self.log.append(f"{ev['name']} {'성공' if ok else '실패'}")
                if leave:
                    p.progress = min(1.0, p.progress + leave / self.total_cycles)
                    p.update_rank()
        if p.progress >= 1.0 - 1e-9:
            self._finish(self.judge_ending())
            return
        self.cycle += 1
        if self.autosave:
            self.saver.save(self.to_dict())
        self._start_morning()

    def _check_fail(self):
        p = self.player
        if p.stats["hp"] <= 0:
            self.log.append("의병전역")
            self._finish(data.FAIL_ENDING)
            return True
        if p.stats["mental"] <= 0:
            self.log.append("탈영")
            self._finish(data.FAIL_ENDING)
            return True
        return False

    def _finish(self, ending):
        self.ending = ending
        self.state = "ending"
        self._say(f"엔딩: {ending}")
        if self.autosave:
            self.saver.save_collection(ending)
            self.saver.delete_save()

    # ------------------------------------------------------------ 엔딩 판정
    def judge_ending(self):
        p, s, r = self.player, self.player.stats, self.rng
        for name in data.RARE_ENDINGS:
            if r.random() < data.RARE_RATE:
                return name
        if s["intel"] < data.DISCHARGE_INTEL:
            return data.FAIL_ENDING
        if p.accepted_nco and s["hp"] >= 70:
            return "부사관"
        conditions = {
            "pilot": p.branch == "공군" and s["intel"] >= 85 and s["hp"] >= 80,
            "captain": p.branch == "해병대" and s["hp"] >= 85 and s["mental"] >= 80,
            "fishing": s["hp"] >= 80 and s["mental"] >= 75 and 70 <= s["intel"] <= 74,
            "dao": s["mental"] >= 95 and 70 <= s["intel"] <= 79,
            "rest": all(70 <= s[k] <= 79 for k in ("hp", "intel", "mental")),
        }
        for name, key, chance in data.HIDDEN_ENDINGS:
            bonus = p.hidden_bonus if key in ("pilot", "captain") else 0
            if conditions[key] and r.random() < chance + bonus:
                return name
        return self.career()

    def career(self):
        p = self.player
        order = ["intel", "hp", "mental"]  # 같으면 지능, 체력, 정신력 순
        best = max(order, key=lambda k: (p.stats[k], -order.index(k)))
        if p.stats[best] >= data.CAREER_THRESHOLD:
            return data.CAREERS[p.job][order.index(best)]
        return self.rng.choice(data.COMMON_CAREERS[best])
