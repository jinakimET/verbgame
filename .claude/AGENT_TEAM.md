# 뉴스 영어 콘텐츠 팀

```
메인 Claude (직접): 뉴스 검색 → 벤토 카드 → 음성 스크립트
        │
 지나쌤이 음성 mp3 생성 → audio/
        │
 메인: 쉼 구간 + 단어 시각(align_words.py)
        ├─► sync-reel-producer ───────► 04_sync_reel/reel_sync.mp4
        └─► expression-reel-producer ─► 05_expression_reels/expr_NN.mp4  (동시)
                     │
              reel-qa-pusher: 검수 → 커밋 → 푸시
```
- 실행: `/news-reels-team CNN 최신 뉴스로 카드 3장`
- 오케스트레이터: `.claude/skills/news-reels-team/SKILL.md`
- 에이전트: sync-reel-producer, expression-reel-producer, reel-qa-pusher
