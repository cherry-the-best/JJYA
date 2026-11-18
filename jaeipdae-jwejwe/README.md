# 재입대 줴줴이야

전역 일주일 만에 전산 오류로 다시 입대하는 꿈에서 출발한 2D 군 복무 육성 시뮬레이션이다.
육군, 해병대, 공군 중 하나로 입대해 보직을 고르고, 2주를 한 사이클로 삼아 전역까지 버틴다.
전역할 때 스탯과 확률로 직업 엔딩 40종 중 하나가 정해지고, 기준에 못 미치면 입영통지서를 받는다.

- 팀명: 전산오류
- 과목: 소프트웨어 프로젝트 3단계, 국립금오공과대학교 컴퓨터공학전공
- 개발 기간: 2026.11.03 ~ 2026.12.10
- 팀원: 이진철(팀장), 이준희

## 실행

Python 3 표준 라이브러리만 쓴다. 따로 설치할 것은 없다.

```bash
python main.py                      # 게임 실행
python -m unittest discover tests   # 규칙 테스트
python tests/simulate.py 100        # 군별 100판 자동 플레이, 엔딩 분포 출력
```

## 폴더 구조

| 파일 | 역할 | 담당 |
| --- | --- | --- |
| main.py | 실행 진입점 | 공동 |
| ui.py | tkinter 화면 전체. 규칙은 두지 않고 `GameManager.scene()`을 그리기만 한다 | 이진철 |
| minigames.py | 미니게임 15종을 처리하는 6가지 틀 | 이진철 |
| items.py | 아이템, 인벤토리 6칸, PX | 이진철 |
| game.py | GameManager. 사이클 진행, 진급, 해금, 실패와 엔딩 판정, NPC 스레드 | 이준희 |
| characters.py | Player, NPC, Utility AI | 이준희 |
| events.py | 이벤트, 선임 집합 판정, 군별 고유 이벤트 | 이준희 |
| storage.py | save.json, collection.json 저장과 불러오기 | 이준희 |
| data.py | 군, 보직, 스탯 증감, 이벤트, 엔딩, NPC 데이터 | 공동 |
| tests/ | 규칙 테스트와 밸런스 자동 플레이 | 공동 |
| assets/ | 배경, 인물, UI, 미니게임 그림 (PNG) | 이진철 |
| docs/ | 계획서 요약, 일정표, 커밋 가이드 | 공동 |

## UI와 로직의 약속

로직(game.py)은 tkinter를 모른다. 그래서 화면 없이 테스트와 자동 플레이가 가능하다.

- UI가 부르는 함수: `new_game(branch, job)`, `load_game()`, `choose(option_id)`,
  `finish_minigame(grade)`, `start_npc_turn()`, `poll_npc_turn()`
- 로직이 돌려주는 값: `scene()` 하나. 상태, 대사, 선택지, 스탯, 미니게임 이름, 엔딩을 담은 dict다.
- NPC 5명은 저녁이 끝날 때 각자 스레드에서 행동을 계산해 queue에 넣는다.
  화면은 메인 스레드에서 `after()`로 queue를 확인하고 그린다.

## 진행 상황

- [x] 기획, 요구사항, 계획서 (docs/plan.md)
- [x] 파일 구조와 클래스 뼈대, 규칙 테스트, 자동 플레이 스크립트
- [ ] 이벤트와 대사 작성 (목표 30~40개)
- [ ] 미니게임 6가지 틀 화면
- [ ] 그림 리소스
- [ ] 밸런스 수치 조정
- [ ] 해병대, 공군 데이터 보강
