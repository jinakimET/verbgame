# 지나쌤 뉴스 영어 콘텐츠 프로젝트 (verbgame 저장소)

새 세션은 이 파일부터 읽는다. 지나쌤은 한국어로 대화하고, 설명·항목명은 한글, 영어는 표현·예문에만 쓴다. 지나쌤이 "뉴스 만들어"라고 하면 아래를 확인 질문 없이 끝까지 한다.

## 한눈에: 파이프라인 (지나쌤 확정)
1. 뉴스 검색 → 벤토 카드 3장 (스킬 `news-bento-card`)
2. 카드별 음성 + **줌인 싱크 영상 3편** (스킬 `ig-reel-sync-zoomin`). 줌인 영상은 현재 모양이 맞고 바꾸지 않는다.
3. 위 표현 중(또는 추가 검색)에서 **키워드 5개**를 `ig-reel`로 뽑아 대본 작성
4. 키워드마다 **voice sync 영상 1편**(새와 함께, 편마다 다른 모션 스타일)
5. 검수 → 커밋·푸시 (게시는 하지 않는다)

자세한 단계·담당·규칙은 `.claude/skills/news-reels-team/SKILL.md`(오케스트레이터)에 있다. 진행 방식은 이 스킬을 따른다.

## 지나쌤이 정한 규칙 (바꾸지 말 것)
- **에이전트는 영상 렌더·검수에만** 쓴다. 뉴스 검색·카드·대본·음성 생성과 **커밋·푸시는 메인이 직접** 한다. (`.claude/agents/`의 sync-reel-producer=줌인 렌더, expression-reel-producer=키워드 영상 렌더, reel-qa-pusher=검수만, 푸시 안 함)
- 뉴스는 **WebSearch로만** 구한다. cnn.com 등 막힌 페이지는 열려고 하지 않는다(지나쌤이 일부러 열 필요 없다고 함). 검색 요약에서만 확인한 사실은 답변에 알리고 캡션에 "CNN은 ~라고 전했다"로 출처를 붙인다.
- **훅은 `.claude/skills/news-reels-team/hook_patterns.md`(100만 릴스 첫마디 틀 목록)에서 뽑는다.** 같은 틀로 반복하지 않고, 한 번에 만드는 5편은 서로 다른 유형을 쓴다. 사실을 읽어 주는 평서문 훅 금지. 훅 점수는 직접 채점한 값이며 도구 점수라고 쓰지 않는다. 원본 스크린샷: `content/reference/hook-catalog-100man-reels/`.
- 훅은 말(4초 안팎)과 화면(0프레임부터 전체 문구가 보이고, 말하는 순간에 단어가 채워짐)을 따로 쓴다. 화면 글자는 음성과 정확히 같게.
- **마무리 규칙(다음 회차부터):** 마지막 "저장해 두세요" 앞에 그 표현을 한 번 더 말하고 화면에도 크게 보여 준다. (2026-11-23 회차 v3 5편은 적용 전이다.)
- 키워드 영상은 편마다 다른 모션 스타일(리퀴드, 홀로그래픽, 클레이모피즘, 하프톤, 아이소메트릭, 키네틱 타이포, 페이퍼컷아웃, 인피니트 줌, 베이퍼웨이브, 텍스트 스크램블, 바우하우스, 뉴브루탈리즘, 셰이프모프, 파티클, 라인 애니메이션 등)를 섞어 눈길을 끌게. 공통 지시는 `kw3_brief.md`.
- 싱크는 **단어 시각으로만** 맞춘다(추정 금지). 추정이 들어가면 알린다.
- 글자·배경 색 대비는 코드로 계산해 확인한다(큰 글자 3:1, 본문 4.5:1). 순수 검정 대신 near-black.
- 웹 사진·실존 인물 사진은 영상에 쓰지 않는다. 캐릭터는 지나쌤의 초록 새(`content/assets/bird_sprite.png`, 말할 때 입이 열림).
- 팔레트는 `jina-color-chips` 스킬/카드 팔레트 라이브러리(19종)에서 돌려 쓴다. 쓴 번호는 `content/palettes_used.json`.
- 핸들 `지나쌤영어  @jina.ssam_english`는 모든 영상·카드에 넣는다(카드·릴스 y≈1588).

## 음성
- 기본: ElevenLabs로 Claude가 생성(`eleven_v4`, 음성 Bella `hpp4J3VqNfWAUOO0d1Us`). 지나쌤이 "음성은 내가 할게"라고 하면 지나쌤 mp3를 쓴다. 지나쌤의 기존 음성은 `Lauren - Friendly, Comforting and Soft`(voice_id `DODLEQrClDo8wCz460ld`).
- 대본 1편 = 생성 1번, **실패해도 같은 호출을 재시도하지 않는다**(중복 과금). 결제 오류가 나면 멈추고 알린다.
- 단어 시각: 생성 음성은 ElevenLabs 플로우에서 `creative_add_flow_asset_node(generation_id)` → `creative_transcribe_audio(connect_from)`(무료). 지나쌤이 올린 mp3는 쉼 구간 + `tools/align_words.py`(pocketsphinx).
- 생성한 mp3는 `elevenlabsusercontent.com`에서 curl로 내려받는다(`verbgame` 환경만 이 호스트 허용).

## 환경·세션 주의
- 세션은 **`verbgame` 클라우드 환경**으로 시작해야 음성 다운로드가 된다(Default 환경은 막혀 있음).
- 한글 폰트 없으면 `apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra`. 렌더에 `pip install opencv-python-headless scipy pocketsphinx` 필요.
- **스킬은 세션 시작 때 한 번 불러온다.** 지나쌤 컴퓨터/프로젝트에만 있는 스킬(예: `ig-reel-sync-zoomin`을 처음엔 못 찾았음)은 새 세션에서 보이거나, 내용을 붙여 줘야 한다. 이름이 비슷한 스킬(`ig-reel`, `ig-reel-sync-zoomin`, `reel-voice-glass-sync`, `news-bento-card`)을 헷갈리지 말 것: 줌인=카드 칸 확대 영상, glass-sync=새와 함께 하는 키워드 영상.
- 지나쌤이 환경 네트워크 변경(호스트 추가) 요청을 거절한 적이 있다: cnn.com, huggingface, everyday-practice.com. 다시 요청하지 않는다.
- 이 저장소에는 다른 프로젝트 브랜치(`ccr-78c61bfb-6zmxdb`: reel-team 에이전트, words 에피소드)도 있다. 건드리지 않는다.
- git: 개발 브랜치에만 푸시한다. 풀 리퀘스트는 지나쌤이 요청할 때만 만든다. 커밋 메시지 끝에는 세션이 지정한 attribution 줄을 넣는다. 훅이 계속 "커밋·푸시하라"고 알려 준다(작업 중 파일은 커밋해도 된다).

## 폴더 지도
- `content/<날짜>-<slug>/`: 01_news, 02_bento(카드), 03_script(대본·훅), audio(음성·단어 시각), 04_zoom_reels, 06_keyword_reels(`v3/`가 최신 스타일 5편, 상위 폴더는 이전 버전)
- `content/assets/bird_sprite.png`, `content/palettes_used.json`, `content/reference/`(훅 목록 원본)
- `.claude/skills/news-reels-team/`: SKILL.md, hook_patterns.md, kw3_brief.md, `tools/`(render_* 스크립트들)
- 현재 회차: `content/2026-11-23-cnn/` (CNN: COP31 결렬 / 호르무즈 / 추수감사절 폭풍. 키워드 fail to agree on, at the highest level since, leverage, put in jeopardy, nonessential)

## 지나쌤 작업 스타일
- 결과물은 하나씩 확인하며 피드백을 준다("너무 평이하다", "훅이 다 비슷하다" 등). 마음에 안 들면 어디가 문제인지 물어보고, 한 번에 크게 바꾸지 말고 이유를 말해 준다.
- 편한 건 한 번에 돌리는 것. "알아서 해 줘"를 선호하지만 크레딧이 드는 일(음성 생성)은 비용을 알려 준다.
- 말하지 않은 사실을 지어내지 않는다. 확인하지 못한 것은 못 했다고 말한다(싱크는 귀로 확인 못 함 등).
