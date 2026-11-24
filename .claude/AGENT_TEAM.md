# 뉴스 영어 콘텐츠 팀

```
메인 Claude: 뉴스 검색 → 벤토 카드 3장 (news-bento-card)
        │
메인: 카드별 음성 → 단어 시각
        └─► sync-reel-producer ───────► 04_zoom_reels/zoom_card_NN.mp4   (ig-reel-sync-zoomin)
메인: ig-reel 키워드 5개 → 대본 → 음성 → Scribe 단어 시각
        └─► expression-reel-producer ─► 06_keyword_reels/kw_NN.mp4       (reel-voice-glass-sync + 새)
                     │
              reel-qa: 검수만 (커밋·푸시는 메인)
```
- 실행: `/news-reels-team` 또는 "뉴스 만들어"
- 오케스트레이터: `.claude/skills/news-reels-team/SKILL.md`
