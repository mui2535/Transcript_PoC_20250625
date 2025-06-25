# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 16:37:11 2025

@author: 119067
"""

# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 15:16:16 2025

@author: 119067
"""

import time
import whisper
import torch

import os

wd = 'C:/data/ai/transcript/'
prompt = '市道,工期,盛土(もりど),業務,仕様書,工種,地盤,支持力,プレロード,軟弱地盤,対策,現地踏査,ボーリング, 圧密沈下, N値, 擁壁,成果品,圧密,沈下,側方,変形,沈下板,照査'


audio_file = wd + 'small.m4a'
model_size = "large-v3"
wav_file = wd + os.path.splitext(os.path.basename(audio_file))[0] + '.wav'
outFile = wd + model_size+'_' + os.path.splitext(os.path.basename(audio_file))[0] + '.txt'

#WAV変換
from pydub import AudioSegment

audio = AudioSegment.from_file(audio_file)
audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
audio.export(wav_file, format="wav")

device = "cuda" if torch.cuda.is_available() else "cpu"

# 時間計測スタート
start = time.perf_counter()

model = whisper.load_model(model_size,device=device)
#model = whisper.load_model(model_size)
result = model.transcribe(wav_file, fp16=False, verbose=True, initial_prompt=prompt)

# 時間計測エンド（推論が終わった直後でも OK）
end = time.perf_counter()

# 経過時間（秒）
elapsed = end - start
print(f"Total elapsed time: {elapsed:.2f} seconds")

segments = result.get("segments", [])
transcript_lines = [seg["text"].strip() for seg in segments]
transcript_with_newlines = "\n".join(transcript_lines)

with open(outFile, "w", encoding="utf-8") as f:
    f.write(transcript_with_newlines)
