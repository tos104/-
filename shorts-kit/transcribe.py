#!/usr/bin/env python3
"""日本語音声を文字起こしして SRT を書き出す(sherpa-onnx + ReazonSpeech + silero VAD)。

例:
  ffmpeg -i in.mp4 -ac 1 -ar 16000 audio.wav
  python3 transcribe.py audio.wav --model-dir models/sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01 \
      --vad models/silero_vad.onnx --out in.srt
"""
import argparse, os, wave
import numpy as np
import sherpa_onnx


def srt_time(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--vad", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    md = a.model_dir
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=os.path.join(md, "encoder-epoch-99-avg-1.int8.onnx"),
        decoder=os.path.join(md, "decoder-epoch-99-avg-1.onnx"),
        joiner=os.path.join(md, "joiner-epoch-99-avg-1.int8.onnx"),
        tokens=os.path.join(md, "tokens.txt"),
        num_threads=os.cpu_count() or 2,
    )
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = a.vad
    cfg.silero_vad.min_silence_duration = 0.4
    cfg.silero_vad.max_speech_duration = 12
    cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)

    with wave.open(a.wav) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

    segs = []
    def drain():
        while not vad.empty():
            seg = vad.front
            st = rec.create_stream()
            st.accept_waveform(16000, seg.samples)
            rec.decode_stream(st)
            text = st.result.text.strip()
            if text:
                start = seg.start / 16000
                segs.append((start, start + len(seg.samples) / 16000, text))
            vad.pop()

    win = cfg.silero_vad.window_size
    for i in range(0, len(samples), win):
        vad.accept_waveform(samples[i:i + win])
        drain()
    vad.flush()
    drain()

    with open(a.out, "w", encoding="utf-8") as f:
        for n, (s, e, t) in enumerate(segs, 1):
            f.write(f"{n}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n\n")
    print(f"{len(segs)} segments -> {a.out}")


if __name__ == "__main__":
    main()
