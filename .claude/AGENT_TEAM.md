# 뉴스 영어 콘텐츠 에이전트 팀

```
 지나쌤 브리프
     │
 [1] news-scout ──────► 01_news/expressions.json        ← 확인 ①
     │
 [2] bento-designer ──► 02_bento/card_NN.png             ← 확인 ②
     │
 [3] voice-scriptwriter ► 03_script/ (전체 + 표현별)     ← 확인 ③
     │
 지나쌤이 음성 mp3 생성 → audio/
     │
     ├──► [4] sync-reel-producer ───────► 04_sync_reel/reel_sync.mp4
     └──► [5] expression-reel-producer ─► 05_expression_reels/expr_NN.mp4   (병렬)
```

- 오케스트레이터: `.claude/skills/news-reels-team/SKILL.md` (`/news-reels-team`)
- 에이전트 정의: `.claude/agents/*.md`
- 사용 예: `/news-reels-team CNN 금리 뉴스로 카드 2장, 릴스 둘 다`
