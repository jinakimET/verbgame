# 타이핑 교정 릴스 SPEC (어법 · 어휘 공통)

에이전트 팀 전원이 따르는 기준 문서. 계정 스킬 `ig-reel-wronggrammar` / `ig-reel-wrongwords` 의 확정 포맷을 저장소에 옮겨 둔 것이다. 둘이 다르면 지나쌤의 최신 지시 → 이 문서 → 계정 스킬 순으로 따른다.

## 1. 세트와 번호

- 한 세트 = 5편, 수준별 1편씩: **1 중하 · 2 중상 · 3 고하 · 4 고상 · 5 어학**.
- 번호: `세트번호-수준순서` (예: `002-3`). 파일명: `어법002-3_고하.mp4` / `어휘002-3_고하.mp4`.
- 세트 폴더: `reels/sets/grammar-002/`, `reels/sets/words-002/`. 안에 `episodes.json`, 결과는 `out/`.
- 다음 세트 번호와 이미 쓴 포인트는 `reels/status.md` 에서 확인하고, 다 만든 뒤 갱신한다.

## 2. 수준별 대상과 소재

| 순서 | 수준 | 대상 | 어법(wrong grammar) | 어휘(wrong words, 반의어) |
|---|---|---|---|---|
| 1 | 중하 | 중1~2 내신 | to부정사·동명사 기본, 3인칭 단수, 비교급 형태, 시제 기본 | 기초 반의어 (thin/thick) |
| 2 | 중상 | 중3 내신·고입 | 분사(형용사 역할), 관계대명사, 수동태, 현재완료 | 중학 필수 (disappointed/satisfied) |
| 3 | 고하 | 고1 모의고사 | 가정법, 시제 일치, 관계부사, 감정동사 분사 | 고1 수준 (improve/weaken) |
| 4 | 고상 | 고2~3 수능 어법 | 2개 섞기: wish+분사, 도치+수일치, 병렬+준동사 등 → `종합편` | 고2~3 (ambiguous/conclusive) |
| 5 | 어학 | 토익 Part 5·텝스 | 접속사 vs 전치사, 수 일치, 도치, 병렬, 품사 자리 → 2개까지 섞으면 `종합편` | 토익·텝스·수능 고난도 (frugal/wasteful) |

- 한 편에 문장 1개. 어법은 오류 1개(고상·어학은 2개까지). 어휘는 반의어로 바뀐 단어 1개.
- 실제로 학습자가 자주 틀리는 포인트를 고른다. 이전 세트와 같은 포인트·단어 쌍은 쓰지 않는다.
- 틀린 곳 말고는 문장이 완전히 맞아야 하고, 정답은 하나로 분명해야 한다.

## 3. 문장 규칙 (레이아웃)

- 영어는 3줄 이하. 한 줄은 약 27자, 830px 이하(렌더러가 검사).
- 줄은 작가가 직접 나눈다 (`lines` 배열 원소 1개 = 화면 1줄).
- 오류 단어는 줄의 앞쪽~가운데에 둔다. 손글씨 정답이 오른쪽으로 넘치지 않게.
- 오류 표시: `{오답>정답}` 예) `"I want {going>to go}"`.
- 어휘 편 `ko` 는 정답 문장의 번역이고, 정답 단어에 해당하는 한글을 `[[ ]]` 로 감싼다(펜 색으로 표시). 한 줄 900px 이하(약 22자).
- 어법 편 `ko` 는 정답 문장 해석 한 줄.

## 4. 요점 칩

- 어법: `title` 1줄 + (선택) `sub` 한글 풀이 + `rows` 최대 3행 `[영어, 한글 뜻]`. 고하·고상·어학은 모든 행에 한글 뜻 필수.
- 어휘: `title` = `정답어 ↔ 오답어`, `sub` = `뜻 ↔ 뜻`, `rows` = 관련 반의어 2쌍 `["A ↔ B", "뜻 ↔ 뜻"]`.
- 칩 내용은 팀이 정한 것이므로 전달할 때 "수정 가능"이라고 알린다.

## 5. 연출 (렌더러에 구현됨)

검정 배경 → 상단 난이도 알약 5개(해당 수준만 켜짐, 고상·어학 혼합은 `종합편` 빨간 태그) → 타자 효과음과 함께 영어 타이핑(오답은 처음부터 펜 색) → [어휘: 한글 문장이 점선 박스로 떠오르고 펜 색 화살표가 힌트 단어에서 오답으로] → 펜이 들어와 X 두 번 → 손글씨 정답 → 정답 문장 박스(정리 색, 하이라이트 = 어두운 박스 + 정리 색 글씨, 노출 20% 길게) → 요점 칩 → `@jina.ssam_english` + 저장 배지 → 끝나기 전 스포트라이트 한 번(0.12초 페이드).

- 색: 펜 = 빨강(기본)/노랑/주황/초록/파랑/HEX, 정리 = 코랄 FF8882(기본)/민트/HEX. 세트 단위로 통일. 초록 펜은 초록새와 겹친다고 알린다.
- 안전영역 y 240~1680. 1080×1920, 30fps, H.264 + AAC.
- 초록새: `reels/assets/bird.png`(누끼 PNG)가 있으면 박스 윗변에 앉힌다. 없으면 생략.
- 폰트: `reels/fonts/` 에 Paperlogy(영어·UI), EF 제주돌담(어휘 한글 문장·표지), 손글씨 펜 폰트(파일명에 Pen/Hand)를 넣으면 자동 사용. 없으면 나눔스퀘어/DejaVu로 대체(전달 시 알린다).
- 표지는 영상에 넣지 않는다. 요청할 때만 `--cover`.

## 6. 에피소드 JSON

```json
{
  "mode": "grammar",            // grammar | words
  "set": "002",
  "colors": { "pen": "빨강", "accent": "코랄" },
  "episodes": [
    {
      "level": 3,
      "points": ["가정법 과거"],      // 기록용, 고상·어학 혼합은 2개
      "combo": false,                 // 종합편 태그
      "audience": "고1 모의고사",      // 기록용
      "lines": ["If I {know>knew} her", "number, I would call", "her right now."],
      "ko": "그녀 번호를 안다면 지금 바로 전화할 텐데.",
      "chip": {
        "title": "If + 과거, would + V",
        "sub": "현재 사실의 반대",
        "rows": [["If I were you", "내가 너라면"], ["If I had time", "시간이 있다면"]]
      },
      "why_wrong": "현재 사실 반대 가정은 if절에 과거형", // 검수자용
      "trap": "know를 그대로 두는 실수가 흔함"           // 검수자용
    }
  ]
}
```

## 7. 렌더·검수 명령

```bash
python3 reels/render/render_reel.py reels/sets/grammar-002/episodes.json --check    # 레이아웃만 검사 (경고 시 exit 1)
python3 reels/render/render_reel.py reels/sets/grammar-002/episodes.json            # 5편 렌더
python3 reels/render/render_reel.py reels/sets/grammar-002/episodes.json --only 3   # 3번만 다시
python3 reels/render/render_reel.py --cover decide "안 틀리게 쓰는 법" -o reels/sets/grammar-002/out/cover.png
```

`out/` 에 편마다 `__check_pen.png`, `__check_chip.png`, `__check_spot.png`(어휘는 `__check_arrow.png` 추가), `__sheet.png` 가 생긴다. 이 이미지를 직접 열어 겹침·넘침을 확인한다.
