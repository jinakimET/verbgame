# 1편 'trust' 싱크 메모 (voice.mp3, 21.24s, 음성 0.10~21.06s)

문장 경계는 silencedetect 7곳 + 음절 수 비례(0.256s/음절)로 대조해 일치 확인.

| 문장 | 구간(초) | chunk 쉼표 경계 |
|---|---|---|
| S1 When I decide ... time has healed them. | 0.10–8.01 | 2.50 (chance,) / 5.28 (wounds,) |
| S2 But as time goes by, their true colors come out again. | 8.61–11.71 | 10.08 (by,) |
| S3 And when I get hurt the same way, there's no going back. | 12.20–15.33 | 13.86 (way,) |
| S4 They say people never change, but that's not just about them. | 15.99–19.44 | 17.55 (change,) |
| S5 I guess I'm no different. | 19.92–21.06 | – |

## 카드 시작 시각 초안 (voice 기준, 간격 ≥1.4s)
1 give someone a second chance 0.3 · 2 bury the old wounds 4.1 · 3 time heals 7.0 ·
4 true colors 10.2 · 5 there's no going back 14.3 · 6 people never change 16.4 · 7 be no different 20.3

## DUR 계산
마지막 발화끝 21.06 + 0.25 + 5.5 ≈ 26.8s (LOOP_T0 = DUR-0.75)

## 확인 필요 (렌더 단계에서 청취)
S1 안의 쉼 3.95·5.84·7.68 는 chunk 로 쪼갤지 들어보고 결정.
