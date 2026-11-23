# diary-reel-kit — 지나쌤 My English Diary 릴스

릴스(9:16) 한 가지만 만듭니다. 캐러셀·2문장 요약은 하지 않습니다.

## 시작 (세션마다)
```
./setup_fonts.sh
```
폰트 두께 참고: 이 환경엔 Noto CJK Medium/Black 이 없어 Regular/Bold 로 대체합니다.

## 팀 (역할 6)
| # | 역할 | 맡는 일 |
|---|---|---|
| 1 | PD | 재료 점검(메모·voice.mp3·사진 7장), 지난 편 표현·팔레트 중복 확인 |
| 2 | 영어 에디터 | 원문 체크, 최종 일기(4~6문장·25~40초), 한글 해석, ElevenLabs 대본, 표현카드 6~8, 표지 키워드·빈칸 |
| 3 | 컬러 디렉터 | 표지 사진 분석 → 디자이너들이 많이 쓰는 팔레트(Color Hunt·Coolors·Adobe Color) 검색 → 사진과 대비 확인 → **자동 확정** |
| 4 | 음성·싱크 | 문장/쉼 구간(silencedetect 또는 ElevenLabs 받아쓰기), 카드 타이밍, -14 LUFS 믹스 |
| 5 | 릴스 렌더 | render/timing/episode_cfg 수정 → 영상 |
| 6 | QA·카피 | 컨택트 시트·표지 글자 잘림·엔딩=카드 일치 검사, 캡션 |

## 흐름
1. 일기 메모 → 에디터가 검토·대본·카드·표지 키워드
2. 표지 사진 도착 → 컬러 디렉터가 팔레트 확정 → **표지 먼저 렌더해 확인** (음성 불필요)
3. voice.mp3 도착 → 싱크 → 렌더 → 검수
4. 영상 + 표지 PNG + 캡션 전달

## 표지만 먼저 (음성 없이)
에피소드 폴더 `episodes/<주제>/` 에 `cover.jpg` 와 `cover.json` 을 두고:
```
python3 covers.py episodes/<주제>/cover.json
```
→ `표지_<주제>.png` + `cover_prev.jpg`. 형식은 `covers.py` 맨 위 설명 참고.
키워드·영어 줄이 화면 폭을 넘으면 경고가 뜹니다.

## 캡션 (확정)
짧은 도입(일기 한 줄 감성) → 오늘의 표현 목록(영/한) → `오늘 일기, 두 줄만 따라 써 보세요 ✍️` → 해시태그
`#지나쌤영어 #realvibejina #영어공부하자 #영어일기 #영어표현`

## 알려진 제약
- 영상 렌더(`render*.py`)는 import 시점에 `voice_pad.wav` 를 읽으므로 `make_audio.py` 이후에만 실행됩니다.
- `render.py` / `timing.py` / `render2.py` 에는 이전 편(가을 팔레트) 값이 남아 있습니다. 새 편마다 팔레트·문장·카드·사진 초점을 교체하세요.
