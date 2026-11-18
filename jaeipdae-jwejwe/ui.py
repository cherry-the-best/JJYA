"""tkinter 화면. 게임 규칙은 하나도 두지 않고 GameManager.scene()을 그리기만 한다.

지금은 뼈대다. 그림 리소스가 준비되면 Canvas에 배경과 인물을 올리고,
미니게임은 6가지 틀별 화면으로 바꾼다.
"""

import tkinter as tk

import data
from game import GameManager

WIDTH, HEIGHT = 1280, 720
FONT = ("맑은 고딕", 12)
FONT_BIG = ("맑은 고딕", 24, "bold")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("재입대 줴줴이야")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.game = GameManager()
        self.frame = None
        self.show_title()

    def clear(self):
        if self.frame:
            self.frame.destroy()
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

    # ------------------------------------------------------------ 타이틀
    def show_title(self):
        self.clear()
        tk.Label(self.frame, text="재입대 줴줴이야", font=FONT_BIG).pack(pady=80)
        tk.Button(self.frame, text="새 게임", font=FONT, width=20,
                  command=self.show_branch_select).pack(pady=6)
        cont = tk.Button(self.frame, text="이어하기", font=FONT, width=20, command=self.continue_game)
        cont.pack(pady=6)
        if self.game.saver.load() is None:
            cont.config(state="disabled")
        tk.Button(self.frame, text="엔딩 도감", font=FONT, width=20,
                  command=self.show_collection).pack(pady=6)
        tk.Button(self.frame, text="종료", font=FONT, width=20, command=self.root.destroy).pack(pady=6)

    def continue_game(self):
        if self.game.load_game():
            self.render()

    def show_collection(self):
        self.clear()
        seen = self.game.saver.load_collection()
        tk.Label(self.frame, text="엔딩 도감", font=FONT_BIG).pack(pady=20)
        text = "\n".join(f"{name}  ({date})" for name, date in seen.items()) or "아직 본 엔딩이 없다."
        tk.Label(self.frame, text=text, font=FONT, justify="left").pack()
        tk.Button(self.frame, text="타이틀로", font=FONT, command=self.show_title).pack(pady=20)

    # ------------------------------------------------------------ 군, 보직 선택
    def show_branch_select(self):
        self.clear()
        tk.Label(self.frame, text="어느 군으로 입대할까?", font=FONT_BIG).pack(pady=40)
        for branch, info in data.BRANCHES.items():
            tk.Button(self.frame, text=f"{branch}  ({info['months']}개월)", font=FONT, width=24,
                      command=lambda b=branch: self.show_job_select(b)).pack(pady=6)

    def show_job_select(self, branch):
        self.clear()
        tk.Label(self.frame, text="어떤 보직을 선택하시겠습니까?", font=FONT_BIG).pack(pady=30)
        for job in data.jobs_for(branch):
            bonus = ", ".join(f"{data.STAT_LABELS[k]} +{v}" for k, v in data.JOB_BONUS[job].items())
            games = ", ".join(data.JOB_MINIGAMES[job])
            label = f"{data.JOB_NAMES[job][branch]}   {bonus}   미니게임: {games}"
            tk.Button(self.frame, text=label, font=FONT, width=70,
                      command=lambda j=job: self.start(branch, j)).pack(pady=4)
        tk.Button(self.frame, text="← 군 다시 선택", font=FONT,
                  command=self.show_branch_select).pack(pady=20)

    def start(self, branch, job):
        self.game.new_game(branch, job)
        self.render()

    # ------------------------------------------------------------ 메인
    def render(self):
        scene = self.game.scene()
        if scene["state"] == "ending":
            return self.show_ending(scene)
        self.clear()
        st = scene["status"]
        stats = "   ".join(f"{data.STAT_LABELS[k]} {v}" for k, v in st["stats"].items())
        bar = f"{st['branch']} {st['rank']} {st['job']} | {stats} | 진행률 {st['progress']}% | {st['cycle']}사이클"
        tk.Label(self.frame, text=bar, font=FONT, anchor="w", bg="#e1e1e1").pack(fill="x")

        # 장면 영역: 그림 리소스가 생기면 배경과 인물을 그린다
        canvas = tk.Canvas(self.frame, width=WIDTH, height=380, bg="#f3ead6", highlightthickness=0)
        canvas.pack()
        canvas.create_text(WIDTH // 2, 190, text=f"[{scene['state']}]", font=FONT_BIG)

        tk.Label(self.frame, text=scene["text"], font=FONT, justify="left",
                 wraplength=WIDTH - 80).pack(pady=10)
        row = tk.Frame(self.frame)
        row.pack()
        for option_id, label in scene["options"]:
            tk.Button(row, text=label, font=FONT,
                      command=lambda o=option_id: self.on_choose(o)).pack(side="left", padx=6)

        if scene["state"] == "minigame":
            self.show_minigame_stub(scene["minigame"])
        elif scene["state"] == "npc":
            self.game.start_npc_turn()
            self.root.after(30, self.wait_npcs)

    def on_choose(self, option_id):
        self.game.choose(option_id)
        self.render()

    def wait_npcs(self):
        # 화면은 메인 스레드에서만 바꾼다. NPC 결과는 queue로 받아 after()로 확인
        if self.game.poll_npc_turn():
            self.render()
        else:
            self.root.after(30, self.wait_npcs)

    def show_minigame_stub(self, name):
        """임시 미니게임 화면. 6가지 틀이 완성되면 교체한다."""
        row = tk.Frame(self.frame)
        row.pack(pady=10)
        tk.Label(row, text=f"{name} (임시) 결과를 고르세요", font=FONT).pack(side="left", padx=6)
        for grade in ("상", "중", "하"):
            tk.Button(row, text=grade, font=FONT, width=4,
                      command=lambda g=grade: self.on_minigame(g)).pack(side="left", padx=3)

    def on_minigame(self, grade):
        self.game.finish_minigame(grade)
        self.render()

    def show_ending(self, scene):
        self.clear()
        tk.Label(self.frame, text=scene["ending"], font=FONT_BIG).pack(pady=80)
        tk.Label(self.frame, text="\n".join(list(self.game.log)[-5:]), font=FONT).pack()
        tk.Button(self.frame, text="엔딩 도감 보기", font=FONT, command=self.show_collection).pack(pady=10)
        tk.Button(self.frame, text="타이틀로 돌아가기", font=FONT, command=self.show_title).pack()
