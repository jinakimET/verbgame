# 타이핑 교정 릴스 에이전트 팀

Claude Code 에서 이렇게 말하면 된다:

- `5수준 wrong grammar 만들어` → 어법 세트 5편(중하·중상·고하·고상·어학)
- `wrong words 세트 만들어줘` → 어휘 세트 5편
- `토익용 어법 1편` / `중학생용 어휘 2편` → 해당 수준만
- `grammar 003-2 다시, 문장 바꿔줘` → 그 편만 수정

```
요청 ─▶ reel-team(팀장)
          ├─ reel-planner   수준별 포인트 기획 (status.md 로 중복 방지)
          │      └─ 지나쌤 확인: 기획 OK? 펜 색? 정리 색?
          ├─ reel-writer    episodes.json 작성 + 레이아웃 검사
          ├─ reel-checker   문법·해석·칩 독립 검수 ⇄ writer (최대 2회)
          └─ reel-renderer  mp4 렌더 + 프레임 QA
       ─▶ mp4 전달 + status.md 갱신
```

| 폴더 | 내용 |
|---|---|
| `SPEC.md` | 포맷·수준·문장 규칙·JSON 형식 (팀 공통 기준) |
| `status.md` | 세트별 제작 현황 |
| `render/render_reel.py` | episodes.json → mp4 (PIL + ffmpeg, 합성 효과음) |
| `fonts/` | Paperlogy, EF 제주돌담, 손글씨 펜 폰트(파일명에 Pen/Hand)를 넣으면 자동 사용 |
| `assets/bird.png` | 초록새 누끼 PNG (넣으면 정답 박스 위에 앉음) |
| `sets/` | 세트별 episodes.json, 결과는 `out/` (git 제외) |
