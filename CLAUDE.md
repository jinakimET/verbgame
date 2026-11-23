# verbgame

- `index.html`, `typing.html`: 불규칙 동사 게임 (정적 HTML).
- `reels/`: 지나쌤 타이핑 교정 릴스(어법 wrong grammar / 어휘 wrong words) 제작 파이프라인.
  - 릴스 요청("5수준 wrong grammar 만들어", "어휘 세트", "003-2 다시")은 `reel-team` 스킬로 처리한다.
  - 팀원: `.claude/agents/` 의 reel-planner · reel-writer · reel-checker · reel-renderer.
  - 기준 문서 `reels/SPEC.md`, 현황 `reels/status.md`, 렌더러 `reels/render/render_reel.py`.
  - 한글 폰트가 없으면 `apt-get install -y fonts-nanum`.
