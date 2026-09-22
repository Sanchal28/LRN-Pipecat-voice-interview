import os
from dotenv import load_dotenv

load_dotenv()

deepgram_key = os.getenv("DEEPGRAM_API_KEY")

if deepgram_key:
    print("Deepgram API key loaded successfully!")
else:
    print("Deepgram API key NOT found!")