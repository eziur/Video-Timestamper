import whisper
from fastapi import FastAPI
import ffmpeg

app = FastAPI()


model = whisper.load_model("turbo")
result = model.transcribe("video.mp4")
print(result["text"])