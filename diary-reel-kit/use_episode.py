"""에피소드 전환: python3 use_episode.py <이름>
 episodes/<이름>/config/{timing,episode_cfg,palette,exprs}.py 를 kit 루트로 복사하고
 voice.mp3 · photos 를 연결한다. (쇼츠 render3.py / make_audio.py / youtube16.py 가 kit 루트를 읽음)
 저장: python3 use_episode.py <이름> --save   (현재 kit 루트 설정을 episodes/<이름>/config 로 보관)"""
import os, sys, shutil
H = os.path.dirname(os.path.abspath(__file__)); name = sys.argv[1]
ep = os.path.join(H, "episodes", name); cfg = os.path.join(ep, "config"); FILES = ["timing.py", "episode_cfg.py", "palette.py", "exprs.py"]
if "--save" in sys.argv:
    os.makedirs(cfg, exist_ok=True)
    for f in FILES: shutil.copy(os.path.join(H, f), os.path.join(cfg, f))
    print("보관:", cfg)
else:
    for f in FILES: shutil.copy(os.path.join(cfg, f), os.path.join(H, f))
    for link, tgt in (("voice.mp3", "episodes/%s/voice.mp3" % name), ("photos", "episodes/%s/photos" % name)):
        p = os.path.join(H, link)
        if os.path.islink(p) or os.path.exists(p): os.remove(p) if os.path.islink(p) else shutil.rmtree(p)
        os.symlink(tgt, p)
    print("전환:", name)
