---
name: news-reels-team
description: "뉴스 검색 → 벤토 카드 → 음성 스크립트까지는 메인 Claude가 직접 만들고, 음성 mp3가 오면 싱크 릴스·표현별 릴스 렌더와 검수·푸시만 에이전트에게 맡기는 파이프라인. '뉴스로 카드랑 릴스 만들어줘', '뉴스 콘텐츠 팀 돌려줘' 같은 요청에 사용."
---

# 뉴스 콘텐츠 팀 (메인 + 렌더 에이전트)

## 역할 분담
| 단계 | 담당 | 내용 |
|---|---|---|
| 1 뉴스·표현 선별 | **메인이 직접** | WebSearch로 최신 기사 검색, `news-bento-card` §1 |
| 2 벤토 카드 | **메인이 직접** | `news-bento-card` §2~5, PNG를 SendUserFile로 전달 |
| 3 음성 스크립트 | **메인이 직접** | 항목마다 ① 표현 ② 영어 예문 ③ 한글 해석 |
| — | 지나쌤 | 스크립트로 음성 mp3 생성 후 업로드 (`audio/voice_full.mp3`) |
| 4 싱크 릴스 | `sync-reel-producer` | 전체 음성 1편 렌더 |
| 5 표현별 릴스 | `expression-reel-producer` | 표현 1개 = 영상 1개, 4와 **동시에** 렌더 |
| 6 검수·푸시 | `reel-qa-pusher` | 프레임·ffprobe 확인, 커밋·푸시 |

에이전트는 4~6단계에서만 쓴다. 1~3단계에 에이전트를 부르지 않는다.

## 규칙
- **기사는 검색으로만**: cnn.com 등 막힌 페이지를 열려고 하지 않는다. 제목·검색 요약으로 확인한 표현만 쓰고, 제목에 없고 요약에서만 확인한 표현은 답변에 한 줄로 알린다.
- **환경**: 한글 폰트 `fonts-noto-cjk`, `fonts-noto-cjk-extra`(Black 두께)가 없으면 apt로 설치. 새 환경 권한 요청은 하지 않는다.
- 게시는 하지 않는다. 결과물과 푸시까지만.

## 작업 폴더 `content/<YYYY-MM-DD>-<slug>/`
```
01_news/ articles.md, expressions.json
02_bento/ card_NN.html/png, cards.json
03_script/ voice_script.txt, sync_scenes.json, expr_scripts.json
audio/ voice_full.mp3, words.json
04_sync_reel/ reel_sync.mp4, frames/
05_expression_reels/ expr_NN.mp4, captions.md, frames/
```
공용 캐릭터: `content/assets/bird_sprite.png` (배경 제거본, 몸통만).
`expressions.json` 항목: `{id, card, slot, type, term, meaning_ko, example_en, example_ko, highlight, source_url}`. id는 모든 단계의 연결 키. 카드 칸에 맞추려 예문을 줄이면 expressions.json도 같이 고친다.

## 음성 후 처리 (메인이 먼저, 에이전트 호출 전)
1. 음성을 `audio/voice_full.mp3`로 복사. `silencedetect=noise=-35dB:d=0.25`로 쉼 구간을 찾고, 1초가 넘는 쉼 11개가 항목 12개를 가르는지 확인.
2. 단어 시각: `python3 align_words.py <작업폴더>` (pocketsphinx 강제 정렬, `pip install pocketsphinx`). `audio/words.json` 생성. ElevenLabs 연결은 파일 업로드가 안 되고 모델 호스트는 막혀 있어서 이 방법을 쓴다.
3. 정렬은 항목 첫 단어가 최대 약 1초 일찍 잡힐 수 있다. 에이전트에게 "예문 첫 단어가 첫 발화 구간 안에서 두 번째 단어와 함께 다음 구간에 있으면 그 구간 시작으로 맞춤"을 알려 준다.

## 에이전트 호출
`sync-reel-producer`와 `expression-reel-producer`를 한 번에 병렬 호출. 프롬프트에 작업 폴더, 단어 시각 사용법, 캐릭터 파일 경로를 넣는다. 둘 다 끝나면 `reel-qa-pusher` 호출 후 mp4를 SendUserFile로 전달하고 출처를 답변 끝에 붙인다.
