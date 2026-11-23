#!/bin/bash
# 세션 시작할 때 한 번: 한글/손글씨/Inter 폰트 + 파이썬 패키지 설치 (이미 있으면 건너뜀)
set -e
need=0
[ -f /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc ] || need=1
[ -f /usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrechorus-mediumitalic.otf ] || need=1
[ -f /usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf ] || need=1
if [ $need = 1 ]; then
  apt-get update -qq && apt-get install -y -qq fonts-noto-cjk fonts-texgyre fonts-inter
fi
python3 -c "import cv2, scipy, PIL, numpy" 2>/dev/null || pip install -q opencv-python-headless scipy pillow numpy
echo "폰트·패키지 준비 완료"
