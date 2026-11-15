"""Pewaktuan caption: potong audio pada lembah energi, transkripsikan tiap potongan dengan Whisper medium."""
import sys, json, wave, numpy as np, sherpa_onnx
import os
md=os.environ.get('WHISPER_MEDIUM_DIR','sherpa-onnx-whisper-medium')  # folder model; lihat qa/audio_transkripsi.py
rec=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f'{md}/medium-encoder.int8.onnx',decoder=f'{md}/medium-decoder.int8.onnx',tokens=f'{md}/medium-tokens.txt',language='id',task='transcribe',num_threads=4)
out={}
for path in sys.argv[2:]:
    w=wave.open(path); sr=w.getframerate(); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
    hop=int(sr*0.01); win=int(sr*0.03)
    rms=np.array([np.sqrt(np.mean(a[i:i+win]**2)+1e-12) for i in range(0,len(a)-win,hop)])
    sm=np.convolve(rms,np.ones(9)/9,mode='same'); db=20*np.log10(sm+1e-9)
    thr=np.percentile(db,18)
    # lembah: titik minimum lokal di bawah ambang, jarak antarpotongan >= 0.9 dtk
    cuts=[]; i=0
    low=db<thr
    while i<len(db):
        if low[i]:
            j=i
            while j<len(db) and low[j]: j+=1
            if (j-i)>=6:
                k=i+int(np.argmin(db[i:j])); t=k*0.01
                if t>0.5 and t<len(a)/sr-0.5 and (not cuts or t-cuts[-1]>=0.9): cuts.append(round(t,2))
            i=j
        else: i+=1
    bounds=[0.0]+cuts+[round(len(a)/sr,2)]
    segs=[]
    for s,e in zip(bounds,bounds[1:]):
        seg=a[int(s*sr):int(e*sr)]
        st=rec.create_stream(); st.accept_waveform(sr,seg); rec.decode_stream(st)
        segs.append({'start':s,'end':e,'text':st.result.text.strip()})
    out[path.split('/')[-1]]={'threshold_db':round(float(thr),1),'segments':segs}
    print(path.split('/')[-1]); [print('  %5.2f–%5.2f  %s'%(x['start'],x['end'],x['text'])) for x in segs]
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=1)
