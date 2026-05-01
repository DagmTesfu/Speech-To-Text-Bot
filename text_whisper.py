import whisper
import requests
import tempfile
import os

# Load model
print("Loading Whisper...")
model = whisper.load_model("base")

# Download a sample audio file
url = "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav"
response = requests.get(url)

# Save to temporary file (Whisper needs a real file or numpy array)
with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
    tmp_file.write(response.content)
    tmp_path = tmp_file.name

print(f"Saved to: {tmp_path}")

# Transcribe
print("Transcribing...")
result = model.transcribe(tmp_path)
print(f"Transcription: {result['text']}")

# Clean up
os.unlink(tmp_path)
print("Done!")