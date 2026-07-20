import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

TOP_K = 6
CHAT_HISTORY_WINDOW = 10
