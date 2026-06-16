import os
from dotenv import load_dotenv

load_dotenv()

# GROQ API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Retrieval settings
TOP_K = 6