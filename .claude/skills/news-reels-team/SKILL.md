---
name: news-reels-team
description: "'뉴스 만들어'라고만 해도 뉴스 검색 → 벤토 카드 3장 → 카드별 음성·줌인 싱크 영상 3편 → 검수·푸시까지 한 번에 끝내는 파이프라인(키워드 영상은 2026-11-25부터 중단). '뉴스로 카드랑 릴스 만들어줘', '뉴스 콘텐츠 팀 돌려줘' 요청에 사용."
---

# 뉴스 만들어 (원스톱: 카드 + 줌인 영상까지)

**입력 기사에 따라 갈린다:** 영문 기사 → 아래 흐름(벤토 카드 + 줌인 영상). **한글 기사 → `kr_carousel.md`**(영어 표현 5개를 뽑아 스큐어모피즘/네오브루탈리즘 캐러셀, 에이전트 `carousel-producer`).

지나쌤이 "뉴스 만들어"라고만 하면 아래를 **확인 질문 없이** 끝까지 한다. 기본값: CNN 최신 뉴스, 카드 3장(표현 12개), 줌인 영상 3편. 지나쌤이 "음성은 내가 할게"라고 하면 해당 단계에서 멈추고 mp3를 기다린다.

**키워드 영상(새와 함께 하는 표현별 영상)은 2026-11-25에 지나쌤이 중단했다. 만들지 않는다.** 방식은 지나쌤이 다시 정한다. 예전 문서·스크립트·에이전트는 `_keyword_archive/`에 보관(README 참고). 지나쌤이 다시 요청하기 전에는 키워드 대본·음성·영상을 만들지 않는다.

## 흐름 (지나쌤 확정)
| 단계 | 담당 | 스킬 | 내용 |
|---|---|---|---|
| 1 카드 | 메인 | `news-bento-card` | WebSearch로 기사(막힌 페이지는 열지 않음), 표현 12개, 카드 3장. 팔레트는 `content/palettes_used.json`에서 안 쓴 것 3개 |
| 2 줌인 영상 | 메인(대본·음성) + 에이전트(렌더) | `ig-reel-sync-zoomin` | 카드 1장 = 영상 1편. 칸 A→B→C→D가 항목 1~4 문장에 맞춰 확대됐다 돌아옴. 카드별 음성 1개(항목 4개: 표현 → 영어 예문 → 해석 순). 줌인 영상은 현재 모양이 맞고 바꾸지 않는다 |
| 3 검수·푸시 | `reel-qa-pusher` | | ffprobe·프레임 확인 후 커밋·푸시 |
| 4 전달 | 메인 | | 카드 PNG, 줌인 영상, 캡션, 출처 |

표현별 릴스 12편(예전 `05_expression_reels`)과 키워드 영상은 이 흐름에 없다.

## 음성
- 기본: Claude가 ElevenLabs로 생성. 모델 `eleven_v4`, 음성 Bella(`hpp4J3VqNfWAUOO0d1Us`) 또는 지나쌤이 지정한 음성. 지나쌤이 직접 만들었다고 올린 mp3가 있으면 그것을 쓴다.
- 대본 1편 = 생성 1번(`creative_generate_speech`, generations_count=1, 줄마다 줄바꿈, flow 하나에 모음). **재시도하지 않는다.** 실패(예: 결제 오류)하면 멈추고 지나쌤에게 원인을 알린다.
- 완료되면 `content_url`을 curl로 `audio/`에 저장(`elevenlabsusercontent.com`은 `verbgame` 환경에서 허용).
- 단어 시각: `creative_add_flow_asset_node(generation_id)` → `creative_transcribe_audio(connect_from)`(무료)로 한글·영어 단어 시각. `words`를 `audio/words_*.json`에 저장. 줌인은 항목의 첫 단어 시작~마지막 단어 끝을 쓴다. 지나쌤 mp3는 `tools/align_words.py` 또는 1초 넘는 쉼으로 항목을 가른다(싱크 추정 금지).
- **숫자·연도는 영어로 읽는다(지나쌤 확정).** 대본 spoken에는 영어 철자로 쓴다(2008 → "twenty oh-eight"). 화면 글자는 숫자로 두되 뜻은 같게. 단, 한국어 문장 속에서 영어 철자 숫자가 한국어로 읽힌다는 지나쌤 지적이 있었다(11-25 kw_04·kw_09). 받아 적기 도구는 영어로 들었다고 나온다. 줌인 음성을 만든 뒤 숫자 부분을 지나쌤이 확인하도록 시각을 알려 준다.

## 에이전트 호출
한글 기사 캐러셀: `carousel-producer`(렌더) → `reel-qa-pusher`(검수·푸시). 2단계 렌더: `sync-reel-producer`(줌인 스킬 경로 + 입력 범위 + 새 스프라이트 지정). 마지막에 `reel-qa-pusher`. 모든 스크립트는 `NEWS_ROOT=<작업 폴더>`를 받는다. 재사용 스크립트는 `tools/`(build_cards, render_zoom, bird, align_words, make_sprite).

## 폴더·규칙
- `content/<날짜>-<slug>/`: 01_news, 02_bento, 03_script, audio, 04_zoom_reels. 공용 `content/assets/bird_sprite.png`.
- 한글 폰트 없으면 `apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra`. 렌더에 `pip install opencv-python-headless scipy pocketsphinx`. 게시는 하지 않고 푸시까지.
