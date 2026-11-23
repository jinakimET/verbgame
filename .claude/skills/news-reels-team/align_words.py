import json, re, subprocess, sys
from pocketsphinx import Decoder
W=sys.argv[1] if len(sys.argv)>1 else '.'
mp3=W+'/audio/voice_full.mp3'
ex=json.load(open(W+'/01_news/expressions.json'))
dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',mp3]))
out=subprocess.run(['ffmpeg','-i',mp3,'-af','silencedetect=noise=-35dB:d=0.25','-f','null','-'],capture_output=True,text=True).stderr
ss=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)]; se=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]
sil=list(zip(ss,se))
# speech segments
segs=[]; t=0.0
for a,b in sil:
    if a-t>0.05: segs.append([t,a])
    t=b
if dur-t>0.05: segs.append([t,dur])
# items split at long silences (>0.9s)
items=[[segs[0]]]
for i in range(1,len(segs)):
    gap=segs[i][0]-segs[i-1][1]
    if gap>0.9: items.append([])
    items[-1].append(segs[i])
assert len(items)==12, len(items)
pcm=subprocess.check_output(['ffmpeg','-v','error','-i',mp3,'-ac','1','-ar','16000','-f','s16le','-'])
def clean(s):
    s=s.replace('~','').replace('A toward B','A toward B')
    s=re.sub(r"[^A-Za-z0-9' ]",' ',s).lower()
    s=s.replace('2008','two thousand eight')
    return ' '.join(s.split())
res=[]
for e,it in zip(ex,items):
    eng0,eng1=it[0][0],it[-2][1]; kor=it[-1]
    text=clean(e['term'])+' '+clean(e['example_en'])
    d=Decoder(samprate=16000,loglevel='FATAL')
    words=text.split()
    oov=[w for w in set(words) if d.lookup_word(w) is None]
    if oov: print('OOV',e['id'],oov); 
    d.set_align_text(text)
    a=max(0,eng0-0.15); b=eng1+0.15
    d.start_utt(); d.process_raw(pcm[int(a*16000)*2:int(b*16000)*2],full_utt=True); d.end_utt()
    ws=[(s.word,round(a+s.start_frame/100,2),round(a+(s.end_frame+1)/100,2)) for s in d.seg() if s.word not in ('<s>','</s>','<sil>','(NULL)')]
    res.append({'id':e['id'],'segments':it,'eng_words':ws,'kor':kor})
    print(e['id'],[round(x,2) for s in it for x in s],'\n   ',' '.join(f"{w}@{s}" for w,s,_ in ws))
json.dump(res,open(W+'/audio/words.json','w'),ensure_ascii=False,indent=1)
