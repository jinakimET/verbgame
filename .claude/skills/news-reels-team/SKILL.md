---
name: news-reels-team
description: "뉴스 검색 → 벤토 카드 → 음성 스크립트 → 음성 싱크 릴스 → 표현별 IG 릴스를 에이전트 5명에게 나눠 맡기는 파이프라인. '뉴스로 카드랑 릴스 만들어줘', '뉴스 콘텐츠 팀 돌려줘' 같은 요청에 사용."
---

# 뉴스 콘텐츠 에이전트 팀 (오케스트레이터)

메인 Claude가 **팀장(오케스트레이터)** 역할. 직접 만들지 않고 단계마다 담당 에이전트를 부르고, 사이사이 지나쌤 확인을 받는다.

## 팀 구성

| 단계 | 에이전트 (`.claude/agents/`) | 하는 일 | 쓰는 스킬 | 결과물 |
|---|---|---|---|---|
| 1 | `news-scout` | 최신 뉴스 검색, 학습용 표현 선별 | news-bento-card §1 | `01_news/` |
| 2 | `bento-designer` | 표현으로 벤토 카드 PNG 제작 | news-bento-card §2~5 | `02_bento/` |
| 3 | `voice-scriptwriter` | 카드 기반 음성 스크립트 (전체용 + 표현별) | news-bento-card §4-4, ig-reel | `03_script/` |
| 4 | `sync-reel-producer` | 음성 mp3를 입힌 전체 싱크 릴스 1편 | reel-voice-glass-sync | `04_sync_reel/` |
| 5 | `expression-reel-producer` | 표현 하나 = 영상 하나 IG 릴스 N편 | ig-reel + reel-voice-glass-sync | `05_expression_reels/` |

## 작업 폴더 (에이전트 간 인수인계 계약)

`content/<YYYY-MM-DD>-<slug>/` 하나를 만들고 모든 에이전트가 이 경로를 공유한다.

```
content/2026-11-23-fed-rates/
├─ 01_news/        articles.md (출처·요약), expressions.json
├─ 02_bento/       card_01.png …, card_01.html …, cards.json
├─ 03_script/      voice_script.txt, sync_scenes.json, expr_scripts.json
├─ audio/          voice_full.mp3, expr_01.mp3 … (지나쌤이 올림), words.json
├─ 04_sync_reel/   reel_sync.mp4, frames/
└─ 05_expression_reels/  expr_01.mp4 … expr_NN.mp4, captions.md
```

`expressions.json` 항목 스키마 (모든 단계가 이 id를 기준으로 연결):
```json
{"id":"01","card":1,"slot":"A","type":"표현","term":"come under scrutiny",
 "meaning_ko":"철저한 검토를 받다","example_en":"...","example_ko":"...",
 "highlight":"under scrutiny","source_url":"https://..."}
```

## 진행 순서

1. **브리프 받기**: 주제/매체(기본 CNN), 카드 장수(장당 4개), 릴스 종류(싱크/표현별/둘 다). 빠진 건 기본값으로 진행.
2. `news-scout` 호출 → `expressions.json` 결과를 표로 보여 주고 **확인 ①**.
3. `bento-designer` 호출 → PNG를 SendUserFile(render)로 보여 주고 **확인 ②**.
4. `voice-scriptwriter` 호출 → 스크립트를 코드 블록으로 전달. **확인 ③**.
5. **음성 대기**: 음성은 지나쌤이 직접 만든다(ElevenLabs 생성은 지나쌤이 명시적으로 요청할 때만). `audio/`에 mp3가 들어오면 다음 단계.
6. `sync-reel-producer`와 `expression-reel-producer`를 **병렬로** 호출 (서로 의존 없음, 둘 다 `audio/`와 `03_script/`만 읽음).
7. mp4들을 SendUserFile(attach)로 전달, 출처(Sources) 목록을 답변 끝에 붙인다.

## 팀장 규칙
- 에이전트를 부를 때 작업 폴더 경로와 이번 회차 요구사항(장수, 팔레트 번호 등)을 프롬프트에 꼭 넣는다.
- 각 단계는 앞 단계 파일만 읽는다. 앞 단계를 고쳐야 하면 해당 에이전트를 다시 부른다.
- 실패/보류 사항(예: 단어 시각 없음, 팔레트 색 확인 필요)은 숨기지 않고 지나쌤에게 한 줄로 알린다.
- 게시는 하지 않는다. 결과물까지만.
