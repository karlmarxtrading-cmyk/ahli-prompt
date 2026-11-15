"""Rekaman cara transkripsi audio (Whisper via sherpa-onnx). Memerlukan model yang diunduh terpisah dari
https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models (tidak disertakan: 0,6–1,9 GB).
Pakai: python3 qa/audio_transkripsi.py <folder_model> <small|medium> <keluaran.json> ",id" a1.wav a2.wav ...
(wav mono 16 kHz hasil: ffmpeg -i video.mp4 -ac 1 -ar 16000 a1.wav)"""
import sys, json, wave, numpy as np, sherpa_onnx
model_dir, name = sys.argv[1], sys.argv[2]
out = {}
for lang in sys.argv[4].split(','):
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f'{model_dir}/{name}-encoder.int8.onnx', decoder=f'{model_dir}/{name}-decoder.int8.onnx',
        tokens=f'{model_dir}/{name}-tokens.txt', language=lang, task='transcribe', num_threads=4)
    for path in sys.argv[5:]:
        w = wave.open(path); sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        s = rec.create_stream(); s.accept_waveform(sr, a); rec.decode_stream(s)
        r = s.result
        out.setdefault(path.split('/')[-1], {})[lang or 'auto'] = {'text': r.text, 'lang': getattr(r, 'lang', ''), 'timestamps': [round(t, 2) for t in getattr(r, 'timestamps', [])][:80], 'tokens': list(getattr(r, 'tokens', []))[:80]}
json.dump(out, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: {l: (v['lang'], v['text']) for l, v in d.items()} for k, d in out.items()}, ensure_ascii=False, indent=1))
