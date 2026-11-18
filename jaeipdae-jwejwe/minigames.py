"""미니게임 15종을 6가지 틀로 처리한다.

여기에는 판정 규칙만 둔다. 실제 화면(Canvas)은 ui.py가 그리고,
끝나면 점수 비율(0.0~1.0)을 grade()에 넘겨 상, 중, 하를 받는다.
"""

import data

RANK_LEVEL = {"이병": 0, "일병": 1, "상병": 2, "병장": 3}


class MiniGame:
    base_time = 20.0  # 초

    def __init__(self, name, rank):
        self.name = name
        # 계급이 오를수록 쉬워진다
        self.level = RANK_LEVEL[rank]
        self.time_limit = self.base_time + 3 * self.level

    def grade(self, ratio):
        if ratio >= 0.8:
            return "상"
        if ratio >= 0.5:
            return "중"
        return "하"


class SequenceGame(MiniGame):
    """순서 기억: 레시피, 차량 점검, 공구, 암구호."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.length = 7 - self.level  # 기억할 순서 수


class MashGame(MiniGame):
    """연타: 설거지, 포탄 나르기."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.target = 60 - 8 * self.level


class ReactionGame(MiniGame):
    """반응 클릭: 사격, 경계근무, 타이밍 사격."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.targets = 10
        self.window = 0.8 + 0.2 * self.level  # 클릭 허용 시간(초)


class FindGame(MiniGame):
    """찾기: 고장 부위, 불시 점검."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.spots = 5 - self.level // 2


class InputGame(MiniGame):
    """입력과 퀴즈: 파이썬 빈칸, 공문 타자, 상식 퀴즈."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.questions = 5


class LaneGame(MiniGame):
    """피하기: 3레인 장애물 피하기."""

    def __init__(self, name, rank):
        super().__init__(name, rank)
        self.speed = 8 - self.level
        self.obstacles = 20 - 3 * self.level


KIND = {
    "레시피 순서 기억": SequenceGame, "차량 점검 순서": SequenceGame,
    "공구 순서 기억": SequenceGame, "암구호 외우기": SequenceGame,
    "설거지 연타": MashGame, "포탄 나르기 연타": MashGame,
    "사격": ReactionGame, "경계근무": ReactionGame, "타이밍 사격": ReactionGame,
    "고장 부위 찾기": FindGame, "불시 점검": FindGame,
    "파이썬 빈칸 채우기": InputGame, "공문 타자": InputGame, "군대 상식 퀴즈": InputGame,
    "3레인 장애물 피하기": LaneGame,
}


def minigames_for(job):
    return data.JOB_MINIGAMES[job] + data.COMMON_MINIGAMES


def create(name, rank):
    return KIND[name](name, rank)
