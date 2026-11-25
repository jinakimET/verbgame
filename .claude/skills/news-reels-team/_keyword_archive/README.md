# 키워드 영상 자동 제작 보관함 (2026-11-25 중단)

지나쌤이 2026-11-25에 "키워드 영상 자동 제작은 품이 너무 많이 든다"며 파이프라인에서 뺐다. 지나쌤이 방식을 다시 생각해 정하면 여기서 꺼내 쓴다. 지금은 **아무 것도 자동으로 호출되지 않는다.**
- 문서: `hook_patterns.md`(100만 릴스 첫마디 틀), `kw3_brief.md`, `kw4_brief.md`(키워드 영상 공통 지시)
- 렌더 스크립트: `tools/render_kw3_*`(11-23), `render_kw_1125_*`·`render_kw4_*`(11-25), `render_kw_reels.py`, `render_expr_reels.py`, `render_sync.py`
- 에이전트 정의: `expression-reel-producer.md.txt` (되살리려면 `.claude/agents/expression-reel-producer.md`로 옮기고 확장자 제거)
- 이전에 만든 영상·대본·음성은 `content/2026-11-23-cnn/`, `content/2026-11-25-cnn/`에 그대로 있다.
- 스크립트는 `tools/bird.py`를 import한다. 되살릴 때는 `.claude/skills/news-reels-team/tools`를 `sys.path`에 넣거나 파일을 `tools/`로 되돌린다.
