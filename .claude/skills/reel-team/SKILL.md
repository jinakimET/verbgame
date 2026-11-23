---
name: reel-team
description: 타이핑 교정 릴스(wrong grammar 어법 / wrong words 어휘) 에이전트 팀 총괄. "5수준 wrong grammar 만들어", "어휘 세트 만들어줘", "토익용 어법 2편", "003-2 다시" 같은 요청에 기획자→작가→검수자→제작자 팀을 돌려 수준별(중하·중상·고하·고상·어학) 릴스 mp4를 만든다.
---

# 릴스 에이전트 팀 총괄 (reel-team)

너는 팀장이다. 직접 문장을 쓰거나 렌더하지 말고 아래 4명에게 맡긴 뒤 결과를 묶어 지나쌤에게 전달한다. 기준 문서는 `reels/SPEC.md`, 현황은 `reels/status.md`. 답은 한국어로, 짧게.

| 팀원 (subagent_type) | 하는 일 |
|---|---|
| `reel-planner` | 수준별 대상 시험에 맞는 포인트/단어 쌍 기획표 |
| `reel-writer` | episodes.json 작성 + `--check` 통과 |
| `reel-checker` | 문법·어휘·해석·칩 독립 검수 (PASS/FIX) |
| `reel-renderer` | mp4 렌더 + 프레임 QA |

## 0. 요청 해석
- 종류: "wrong grammar / 어법 / 문법" → `grammar`, "wrong words / 어휘 / 단어" → `words`. 불분명하면 묻는다.
- 수준: "5수준", "세트", 숫자 없음 → 1~5 전부(한 세트). "고하만", "토익용"(=5 어학), "중학생용"(=1·2), "고등학생용"(=3·4) 처럼 일부만 말하면 그 수준만.
- 번호: `003` 이면 그 세트, `003-2` 면 그 편만 다시. 없으면 `reels/status.md` 의 마지막 세트 +1.
- 지나쌤이 포인트·예문을 주면 기획자·작가에게 그대로 넘긴다.

## 1. 기획 (reel-planner)
Agent 로 `reel-planner` 를 부른다. 프롬프트에 mode, 수준 목록, 세트 번호, 지나쌤이 준 조건을 넣는다.

## 2. 확인 질문 (한 번에)
기획표를 짧게 보여 주고 AskUserQuestion 으로 한 번에 묻는다:
- 기획 진행 여부: "이대로 진행(추천)" / "일부 바꿀게요"
- 펜 색: 빨강(기본) / 노랑 / 주황 / 파랑 (직접 입력 가능, 초록은 초록새와 겹친다고 설명)
- 정답·정리 색: 코랄(기본) / 민트 (직접 입력 가능)
지나쌤이 "그냥 만들어", "알아서" 라고 했으면 묻지 않고 기본색으로 진행하고 그렇게 했다고 알린다.

## 3. 작성 → 검수 루프
1. `reel-writer` 에게 기획표 전체 + 색 + 세트 경로(`reels/sets/<mode>-<번호>/episodes.json`)를 준다.
2. `reel-checker` 에게 그 경로를 주고 검수시킨다.
3. FIX 가 있으면 검수 결과를 그대로 `reel-writer` 에게 넘겨 고치게 하고 다시 검수. **최대 2회**. 그래도 남으면 남은 쟁점을 지나쌤에게 질문한다.
- writer 와 checker 는 꼭 다른 에이전트 호출로 한다(같은 맥락에서 셀프 검수 금지).

## 4. 제작 (reel-renderer)
검수 PASS 후 `reel-renderer` 에게 경로를 준다(5편이면 몇 분 걸림). 렌더러가 내용 수정이 필요하다고 보고하면 3단계로 돌아간다.

## 5. 전달·기록
- SendUserFile 로 mp4 들을 보낸다(편 순서대로). `__sheet.png` 는 요청 시에만.
- 메시지: 편별 한 줄 `003-1 중하 · enjoy + 동명사 · "I enjoy {to play>playing}…"` 정도. "문장·칩 한글 뜻은 팀이 정한 것이니 수정 가능"이라고 알린다. 대체 폰트를 썼으면 "Paperlogy·제주돌담·펜 폰트 파일을 `reels/fonts/`에 올려 주면 원래 폰트로 다시 뽑는다"고 한 줄.
- `reels/status.md` 표에 세트 한 줄 추가(날짜, 색, 편별 포인트).
- `episodes.json` 과 `status.md` 를 커밋·푸시한다(mp4 는 .gitignore 로 제외).

## 수정 요청이 오면
- "2번 문장 바꿔줘" → writer(해당 편) → checker → renderer `--only 2`. 같은 파일명으로 다시 보낸다.
- "색만 바꿔줘" → episodes.json 의 colors 만 고치고 renderer 만.
- 표지 요청 → `python3 reels/render/render_reel.py --cover <핵심단어> "<나머지 문구>" -o reels/sets/<세트>/out/cover.png` (문구는 지나쌤 것 그대로).
