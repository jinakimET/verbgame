---
name: news-reels-team
description: "'뉴스 만들어'라고만 해도 뉴스 검색 → 벤토 카드 3장 → 음성 스크립트 → ElevenLabs 음성 생성 → 싱크 릴스 1편 + 표현별 릴스 12편 + ig-reel 키워드 릴스 3편 → 검수·푸시까지 한 번에 끝내는 파이프라인. '뉴스로 카드랑 릴스 만들어줘', '뉴스 콘텐츠 팀 돌려줘' 요청에 사용."
---

# 뉴스 만들어 (원스톱)

지나쌤이 "뉴스 만들어"라고만 하면 아래를 **확인 질문 없이** 끝까지 한다. 기본값: CNN 최신 뉴스, 카드 3장(표현 12개), 싱크 릴스 1편 + 표현별 릴스 12편 + 키워드 릴스 3편. 주제·장수를 말하면 그걸 따른다. 지나쌤이 "음성은 내가 할게"라고 하면 3단계 뒤에 멈추고 `audio/voice_full.mp3` 업로드를 기다린다.

## 분담
| 단계 | 담당 | 내용 |
|---|---|---|
| 1 뉴스·표현 | 메인 | WebSearch만 사용. `news-bento-card` §1. cnn.com 같은 막힌 페이지는 열지 않는다. 제목 밖(검색 요약에서만) 확인한 표현은 답변에 한 줄로 알린다 |
| 2 카드 | 메인 | `tools/build_cards.py`를 템플릿으로 이번 팔레트·내용으로 고쳐 렌더. `content/palettes_used.json`에서 안 쓴 팔레트 3개 선택 후 기록. PNG 5가지 검수 후 SendUserFile |
| 3 스크립트 | 메인 | `03_script/` 3파일: voice_script.txt, sync_scenes.json(split_at=첫 줄 단어 수), expr_scripts.json(화면 훅 후보 3개 직접 채점, 1위 선택) |
| 4 음성 | 메인 | 아래 "음성 자동 생성" |
| 5 단어 시각 | 메인 | 카드 음성(12표현): `NEWS_ROOT=<폴더> python3 tools/align_words.py` → `audio/words.json` (한글 줄은 쉼 구간 사용) |
| 5-2 키워드 릴스 대본 | 메인 | `ig-reel` 방식: 카드마다 키워드 1개(총 3개), 훅 후보 3개 직접 채점(도구 점수라고 쓰지 않음), 말할 대본(훅→이유→본문→마무리, 훅 단어 반복)과 화면 글자를 따로. 사실은 articles.md 범위만. `03_script/keyword_scripts.json` |
| 5-3 키워드 음성 | 메인 | 대본 1편 = 생성 1번(eleven_v4, Bella, 줄마다 줄바꿈). 완료 후 `creative_add_flow_asset_node(generation_id)` → `creative_transcribe_audio(connect_from=그 node_id)`로 **한글·영어 단어 시각**을 무료로 받는다(업로드 불필요). 결과의 `words`를 `audio/words_kw.json`에 저장하고 비트별 첫 단어 시각으로 매핑 |
| 6-2 키워드 릴스 렌더 | 에이전트 | `expression-reel-producer`에 `06_keyword_reels/` 렌더를 맡긴다(6의 두 에이전트와 동시) |
| 6 렌더 | 에이전트 2개 **동시** | `sync-reel-producer`, `expression-reel-producer`(표현별 12편), 키워드 릴스용 `expression-reel-producer` 하나 더. 프롬프트에 폴더, `tools/` 스크립트 재사용(장면 수·팔레트·표현 id만 손보기), 캐릭터 `content/assets/bird_sprite.png`, words.json 사용법을 넣는다 |
| 7 검수·푸시 | `reel-qa-pusher` | ffprobe·프레임 확인, 통과하면 커밋·푸시 |
| 8 전달 | 메인 | 카드 PNG, 싱크 릴스, 표현별 mp4 12개, captions.md 요약, 음성 스크립트 코드 블록, 출처 목록 |

에이전트는 6~7단계에서만 쓴다. 모든 스크립트는 `NEWS_ROOT=<작업 폴더>` 환경변수로 폴더를 받는다.

## 음성 자동 생성 (4단계)
- 모델 `eleven_v4`, 음성 Bella (`hpp4J3VqNfWAUOO0d1Us`, 정보·교육용 목록에서 연간 사용량 1위. 사용량 수치는 API에 안 나와 "20만 이상"은 확인하지 못했다). 지나쌤이 다른 음성을 지정하면 그걸 쓴다.
- **표현마다 한 번씩** `creative_generate_speech`(generations_count=1, 한 flow에 모음). 프롬프트: `<term>. <example_en> <example_ko>` (`~`는 뺀다). 줄 사이 쉼이 약 0.6초 자연스럽게 생긴다(시험 확인). 먼저 `estimate_only`로 총 크레딧을 보고하고, 생성 호출은 **재시도하지 않는다**(재호출 시 이중 과금).
- `creative_get_flow_run_status`로 완료를 기다려 `content_url`을 `curl`로 `audio/expr_NN.mp3`에 저장(호스트 `elevenlabsusercontent.com`은 `verbgame` 환경에서 허용됨). 12개를 항목 사이 1.2초 무음으로 이어 붙여 `audio/voice_full.mp3`. 표현별 릴스는 `expr_NN.mp3`를 그대로 쓴다.
- 지나쌤이 음성이 마음에 안 든다고 하면 그 시점부터 지나쌤 mp3로 5~8단계만 다시 한다.

## 폴더
`content/<날짜>-<slug>/` : 01_news, 02_bento, 03_script, audio, 04_sync_reel, 05_expression_reels. 공용: `content/assets/bird_sprite.png`.
`expressions.json` 항목: `{id, card, slot, type, term, meaning_ko, example_en, example_ko, highlight, source_url}`. 카드 칸에 맞추려 예문을 고치면 expressions.json도 같이 고친다.

## 규칙
- 한글 폰트가 없으면 `apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra`.
- 싱크는 단어 시각으로만(추정 금지). 정렬은 항목 첫 단어가 최대 약 1초 이르게 잡힐 수 있어, 첫 발화 구간 안인지 확인하고 보정.
- 게시는 하지 않는다. 결과물과 푸시까지.
