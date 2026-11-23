# 시안 JSON 형식 (render.js 입력)

```jsonc
{
  "title": "to부정사 부사적 용법 종합편",
  "angle": "A 지도형",                     // 시안 각도 (메모용)
  "palette": ["#2B2B2B", "#D9D9D9", "#FFD84D", "#FAFAF7"],  // 4~5색 → 자동 역할 배정
  // 또는 "palette": {"DK":"#..","BG":"#..","PK":"#..","LP":"#..","SUB":"#..","ACC":"#.."}
  "style": "brutal",                       // brutal(기본) | soft(그림자 흐림·테두리 얇게) | flat(그림자 없음)
  "handle": "@jina.ssam_english",
  "map": ["목적", "감정 원인", "판단 근거", "결과", "형용사 꾸밈"],  // 지도 갈래 이름 (nav 칩)
  "slides": [ ... ]
}
```

모든 문자열에 인라인 표시 사용 가능: `==PK형광펜==` `++LP형광펜++` `@@ACC형광펜@@` `[[덩어리]]` `~~취소~~` `__밑줄__` `{{알약}}` `<br>`

## slides

### 표지 `cover`
```json
{"kind":"cover", "badge":"어법 종합편", "sub":"to부정사 ③ 부사처럼",
 "keywords":"목적 · 감정 · 판단 · 결과 · ==형용사==",
 "example":"I woke up ==to find== snow.",
 "title":["to 하나에", "뜻이 다섯"],          // 둘째 줄 하이라이트. 한 줄 한글 8자 이내
 "desc":"빼 봐도 문장이 멀쩡하면, 부사처럼!",
 "photo":"cover.jpg", "photoPos":"50% 10%"}   // photo 없으면 타이포 표지
```

### 개념 카드 `concept` / 정리 카드 `summary`(어두운 배경)
```json
{"kind":"concept", "label":"① 목적", "nav":1,
 "h2":["~하려고?", "==목적=="],    // 문자열 2개. 둘째 줄은 자동 하이라이트(== 생략 가능)
 "blocks":[ ... ], "gap":26}
```
`nav`: map 갈래 번호(1부터). 0 또는 생략 = 지도 칩 줄 없음.

### 퀴즈 `quiz`
```json
{"kind":"quiz", "label":"확인 퀴즈", "h2":["풀어 보면", "내 것이 돼요"],
 "questions":["I'm sorry ___ you. (hear / to hear)", "..."],
 "answers":["==to hear== (감정 원인)", "..."]}
```

## blocks

| type | 필드 |
|---|---|
| `rows` | `items`: [[영어, 해석], …], `size`(34), `ksize`(26) |
| `point` | `text`, `size`(34) |
| `dark` | `title`(선택, 예 "알고 보면"), `text`, `size`(28) |
| `strip` | `items`: [{`base`, `chunk`, `after`(선택), `verdict`, `ok`(true=완전)}] |
| `vs` | `a`/`b`: {`title`, `lines`:[…], `note`} |
| `trap` | `items`: [{`bad`, `good`, `why`}] |
| `map` | `hub`, `hubSub`, `cols`(2), `items`: [{`label`, `ko`, `en`, `wide`(선택)}] |
| `flow` | `steps`: [문자열…] |
| `cloud` | `title`, `words`: [문자열…] |
| `morph` | `stem`(고정 앞부분), `tails`: [[뒷부분, 뜻]…] |
| `next` | `text` |
| `text` | `text`, `size`(30) — 장식 없는 한 줄 |

## 높이 감각 (1350 중 쓸 수 있는 본문 ≈ 1040px)
- 상단 줄 50 + nav 46 + h2 두 줄 ≈ 200 + 하단 핸들 40
- rows 한 줄 ≈ 70px, point 한 줄 ≈ 50px + 패딩 44, dark 줄 ≈ 44px + 패딩 72
- 렌더러가 넘침을 자동 검사해서 `⚠ slide 05 overflow +84px`처럼 알려 준다 → 문장을 줄이거나 블록을 나눈다.
