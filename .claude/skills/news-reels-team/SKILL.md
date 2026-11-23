---
name: news-reels-team
description: "'뉴스 만들어'라고만 해도 뉴스 검색 → 벤토 카드 3장 → 카드별 음성·줌인 싱크 영상 3편 → ig-reel 키워드 5개 → 키워드별 새 싱크 영상 5편 → 검수·푸시까지 한 번에 끝내는 파이프라인. '뉴스로 카드랑 릴스 만들어줘', '뉴스 콘텐츠 팀 돌려줘' 요청에 사용."
---

# 뉴스 만들어 (원스톱)

지나쌤이 "뉴스 만들어"라고만 하면 아래를 **확인 질문 없이** 끝까지 한다. 기본값: CNN 최신 뉴스, 카드 3장(표현 12개), 줌인 영상 3편, 키워드 영상 5편. 지나쌤이 "음성은 내가 할게"라고 하면 해당 단계에서 멈추고 mp3를 기다린다.

## 흐름 (지나쌤 확정)
| 단계 | 담당 | 스킬 | 내용 |
|---|---|---|---|
| 1 카드 | 메인 | `news-bento-card` | WebSearch로 기사(막힌 페이지는 열지 않음), 표현 12개, 카드 3장. 팔레트는 `content/palettes_used.json`에서 안 쓴 것 3개 |
| 2 줌인 영상 | 메인(대본·음성) + 에이전트(렌더) | `ig-reel-sync-zoomin` | 카드 1장 = 영상 1편. 칸 A→B→C→D가 항목 1~4 문장에 맞춰 확대됐다 돌아옴. 카드별 음성 1개(항목 4개: 표현 → 영어 예문 → 해석 순) |
| 3 키워드 선정 | 메인 | `ig-reel` | 위 표현 중 또는 추가 검색에서 키워드 5개. 훅 후보 3개를 서로 다른 방식으로 직접 채점(도구 점수라고 쓰지 않음), 말할 대본·화면 글자 분리. 사실은 기사 범위만. **훅은 사실을 읽어 주는 평서문 금지**("합의 없이 끝난 회의." ✗). 반응형 "~다고요?", 도전형 "이 표현 몰라요?", 대조형 "A인데 B라고요?" 중에서 고르고 4초 안(말), 화면에는 0프레임부터 큰 글자로. 5편이 같은 틀로 반복되지 않게 방식을 섞는다. **훅은 `hook_patterns.md`(지나쌤의 100만 릴스 첫마디 틀 목록)에서 뽑는다.** 한 번에 만드는 5편은 서로 다른 유형을 쓰고(같은 유형 2편 금지), 편마다 쓴 유형·틀을 `keyword_scripts.json`의 `formula`에 적는다. 뉴스에 없는 사실을 틀에 끼워 넣지 않는다(과장 ✗) |
| 4 키워드 영상 | 메인(음성) + 에이전트(렌더) | `reel-voice-glass-sync` | 키워드 1개 = 영상 1편. 새와 함께 훅에 어울리는 구성. 대본 1편 = 음성 1개 |
| 5 검수·푸시 | `reel-qa-pusher` | | ffprobe·프레임 확인 후 커밋·푸시 |
| 6 전달 | 메인 | | 카드 PNG, 영상, 캡션, 음성 스크립트, 출처 |

표현별 릴스 12편(예전 `05_expression_reels`)은 이 흐름에 없다. 만들지 않는다.

## 음성 (4개 단계에서 공통)
- 기본: Claude가 ElevenLabs로 생성. 모델 `eleven_v4`, 음성 Bella(`hpp4J3VqNfWAUOO0d1Us`) 또는 지나쌤이 지정한 음성. 지나쌤이 직접 만들었다고 올린 mp3가 있으면 그것을 쓴다.
- 대본 1편 = 생성 1번(`creative_generate_speech`, generations_count=1, 줄마다 줄바꿈, flow 하나에 모음). **재시도하지 않는다.** 실패(예: 결제 오류)하면 멈추고 지나쌤에게 원인을 알린다.
- 완료되면 `content_url`을 curl로 `audio/`에 저장(`elevenlabsusercontent.com`은 `verbgame` 환경에서 허용).
- 단어 시각: `creative_add_flow_asset_node(generation_id)` → `creative_transcribe_audio(connect_from)`(무료)로 한글·영어 단어 시각. `words`를 `audio/words_*.json`에 저장. 줌인은 항목의 첫 단어 시작~마지막 단어 끝, 키워드는 비트의 첫 단어 시작을 쓴다. 지나쌤 mp3는 `tools/align_words.py` 또는 1초 넘는 쉼으로 항목을 가른다(싱크 추정 금지).

## 에이전트 호출
2단계 렌더: `sync-reel-producer`(줌인 스킬 경로 + 입력 범위 + 새 스프라이트 지정). 4단계 렌더: `expression-reel-producer`(키워드 영상). 두 렌더는 입력이 모이면 동시에 돌린다. 마지막에 `reel-qa-pusher`. 모든 스크립트는 `NEWS_ROOT=<작업 폴더>`를 받는다. 재사용 스크립트는 `tools/`(build_cards, render_zoom, render_kw_reels, bird, align_words).

## 폴더·규칙
- `content/<날짜>-<slug>/`: 01_news, 02_bento, 03_script, audio, 04_zoom_reels, 06_keyword_reels. 공용 `content/assets/bird_sprite.png`.
- QA: 오른쪽 230px 비움은 키워드 영상에만 적용(줌인은 줌인 스킬 규격).
- 한글 폰트 없으면 `apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra`. 게시는 하지 않고 푸시까지.
