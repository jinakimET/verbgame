# 지나쌤 컬러칩 라이브러리

릴스·카드·캐러셀·표지의 색을 정할 때 여기서 고른다. 같은 세트 안에서는 서로 다른 색상군(보라·초록·남색·주황·핑크 등)을 돌려 쓰고, 보라 계열로만 나오지 않게 한다. 지나쌤이 칩을 더 주면 이 목록에 이어서 추가한다.

## 쓰는 방법
1. 이번 편에 쓸 칩을 하나 고른다. 이미 쓴 칩은 (사용함)으로 표시하고 같은 세트에서 반복하지 않는다.
2. 역할 배치: 배경 / 강조(박스·칩) / 종이(밝은 칸) / 어두운 칸. 글자색은 대비 기준(본문 4.5:1, 큰 글자 3:1)을 코드로 계산해 통과시킨다. 미달이면 색을 어둡게·밝게 조정한다.
3. 순수 검정(#000)은 피하고 #121212~#17191B 같은 near-black을 쓴다.
4. ≈ 표시가 붙은 색은 라벨 헥사와 어긋나 추정한 값이다. 처음 쓸 때 지나쌤에게 한 줄로 확인한다.

## A. 기본 라이브러리 (1~19번, 추천 배치: 배경 · 강조 · 종이 · 어두운 칸)
1. Track Black #17191B, Chalk Grey #E4E3DE, Electric Purple #8B3DFF (사용함: collapse 편)
2. Forest Green #005C47, Crest Yellow #E0F354, Mandarin Orange #FD550A
3. Midnight Navy #1A2841, Old Cream #F0E1CE, Vintage Red #B11722
4. Midnight Ink #080F1B, Azure Blue #329DD2, Vermilion Orange #FF4C2B
5. Grape Purple #4A388E, Soft Lavender #CDC6E4, Mango Yellow #FFBF48
6. Sky Blue #2C99D6, Cloud White #F8FAFC, Scarlet Red #EB2F33
7. Charcoal #121212, Warm White #FDF9EA, Performance Orange #FE5105
8. Court Green #0FA241, Spruce Green #17411B, Tennis Yellow #ECF665
9. Soft Blue #B6DFED, Midnight Navy #002941, Coral Orange #FD6E6E
10. Raven Black ≈#120808, Powder Blue ≈#BDE3F7, Poppy Red ≈#E20C20
11. Jet Black #0B0B0B, Hot Pink #FF2DA8, Chartreuse #D4FF3F
12. Lavender #CBB3E8, Chartreuse #D4FF3F, Tomato Red #E34234
13. Warm Ivory #F9EBD7, Emerald Green #046A38, Vermilion #E34222
14. Soft Peach #F9EAD7, Lime Green #BFE23A, Crimson #E10600
15. Oatmeal #E8DCC6, Pine Green #1F3B2E, Soft Lilac #CBB3E8
16. Dusty Mauve #C9A0A7, Deep Plum #3A0F34, Terracotta #C75A3A
17. Raspberry Pink ≈#C8296B, Mellow White #FEFDFE, Pastel Turquoise ≈#8FF5C8
18. Deep Maroon #250104, Tomato Red #D71A06, Neon Yellow #CDF73D
19. Azure Navy ≈#24508F, Snowy White #FEFDFE, Coral Red #FD614B

## B. Color Hunt 팔레트 (4색)
20. 민트·청록: #E3FDFD #CBF1F5 #A6E3E9 #71C9CE
21. 연핑크: #F9F5F6 #F8E8EE #FDCEDF #F2BED1
22. 코랄·라벤더 그레이: #FFC7C7 #FFE2E2 #F6F6F6 #8785A2
23. 브라운·베이지: #AD8B73 #CEAB93 #E3CAA5 #FFFBE9
24. 슬레이트 블루: #27374D #526D82 #9DB2BF #DDE6ED
25. 핑크·민트: #FFB6B9 #FAE3D9 #BBDED6 #61C0BF

## C. 이미지로 받은 3색 칩
26. Emerald #0F5C45, White #FFFFFF, Tangerine #F28C28
27. Ink Navy #141B2D, Pearl White #F4F1EA, Electric Coral #FF5A4E
28. Sky Blue #59B5FF, White #FFFFFF, Hot Pink #FF50BF
29. Midnight Black #0C0C0C, Electric Blue #2F94DD, Cantaloupe Orange #FF7350
30. #303D5D, #8B613F, #662981
31. #D1C856, #433F33, #734A30
32. #C8D4B0, #306745, #514036
33. #C0BFC3, #C7A4A8, #64556A
34. #0B3B8F, #7C97AE, #F3F4F7
35. #A1BDD6, #EFBDC8, #172645
36. #CDCCCD, #58457C, #B9A07A
37. #E67622, #C7AF93, #804F2D
38. Raspberry Pink #BC164D, Pale Pink #FFD0DF, Butter Yellow #FFE164
39. #347246, #BCCBAE, #A49274
40. Obsidian Black #111217, Ice Grey #DFE5EB, Racing Red #EF233C
41. Galactic Blue #04183B, True Blue #2C92E5, Magenta Pink #ED1F9E
42. Saffron Cherry #6D0317, Rose Red #E52150, Sunshine Yellow #F4EB06

## D. 팬톤 칩 (헥사는 화면에서 잰 근삿값 ≈)
43. Sky Blue 297 C ≈#8CCCE8, Forest Green 5535 C ≈#1E3628, Tangerine 1645 C ≈#E67442
44. Butter Yellow 7401 C ≈#FBE8AD, Raspberry 7636 C ≈#AF2F48, Pistachio 580 C ≈#C7D5A0

## 사용 기록 (뉴스 카드)
쓴 번호: 1~6. 새 회차는 안 쓴 번호를 순서대로 3개 고른다. 10·17·19는 색 확인(≈)이 필요해 마지막 순위.
