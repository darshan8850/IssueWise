import os
from dotenv import load_dotenv

load_dotenv()

# AI Model API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# GitHub App Configuration
APP_ID = os.getenv("APP_ID")
APP_PRIVATE_KEY = os.getenv("APP_PRIVATE_KEY", "").encode().decode("unicode_escape").strip()

# Available Models Configuration
AVAILABLE_MODELS = {
    "mistral": {
        "name": "Mistral AI",
        "model": "mistral-small-latest",
        "api_key": MISTRAL_API_KEY
    },
    "openai": {
        "name": "OpenAI",
        "model": "gpt-4-turbo-preview",
        "api_key": OPENAI_API_KEY
    },
    "claude": {
        "name": "Claude",
        "model": "claude-3-opus-20240229",
        "api_key": CLAUDE_API_KEY
    }
}