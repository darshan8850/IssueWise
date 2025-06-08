import os
from dotenv import load_dotenv
import logging
import base64
import re
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

# AI Model API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GitHub App Configuration
APP_ID = os.getenv("APP_ID")

def load_private_key_from_file(file_path: str) -> str:
    """Load private key from a PEM file."""
    try:
        with open(file_path, 'r') as f:
            key = f.read()
        logger.debug("Successfully loaded private key from file: %s", file_path)
        return key
    except Exception as e:
        logger.error("Failed to load private key from file %s: %s", file_path, str(e))
        raise

def format_private_key(key: str) -> str:
    """Format and validate the private key."""
    # Remove any existing headers/footers and clean up the key
    key = key.replace("-----BEGIN RSA PRIVATE KEY-----", "")
    key = key.replace("-----END RSA PRIVATE KEY-----", "")
    key = key.strip()
    
    # Remove any spaces, newlines, and ensure it's a single line
    key = key.replace(" ", "").replace("\n", "").replace("\\n", "")
    
    # Remove any non-base64 characters
    key = re.sub(r'[^A-Za-z0-9+/=]', '', key)
    
    # Add padding if needed
    padding = len(key) % 4
    if padding:
        key += '=' * (4 - padding)
    
    # Validate the key format
    try:
        # Try to decode the key to ensure it's valid base64
        decoded_key = base64.b64decode(key)
        if len(decoded_key) < 100:  # RSA keys are typically much longer
            raise ValueError("Key appears to be too short for an RSA private key")
    except Exception as e:
        logger.error("Key validation failed: %s", str(e))
        logger.debug("Key length: %d, Key (first 50 chars): %s...", len(key), key[:50])
        raise ValueError(f"Invalid private key format: {str(e)}")
    
    # Format the key with proper line breaks (64 characters per line)
    key_chunks = [key[i:i+64] for i in range(0, len(key), 64)]
    formatted_key = "\n".join([
        "-----BEGIN RSA PRIVATE KEY-----",
        *key_chunks,
        "-----END RSA PRIVATE KEY-----"
    ])
    
    return formatted_key

def load_private_key() -> str:
    """Load private key from file or environment variable."""
    # First try to load from PEM file
    pem_path = os.getenv("APP_PRIVATE_KEY_PATH", "github_app.pem")
    if os.path.exists(pem_path):
        try:
            key = load_private_key_from_file(pem_path)
            return format_private_key(key)
        except Exception as e:
            logger.warning("Failed to load key from file, falling back to environment variable: %s", str(e))
    
    # Fall back to environment variable
    key = os.getenv("APP_PRIVATE_KEY", "")
    if not key:
        raise ValueError("Neither APP_PRIVATE_KEY_PATH nor APP_PRIVATE_KEY environment variables are set")
    
    return format_private_key(key)

try:
    APP_PRIVATE_KEY = load_private_key()
except Exception as e:
    logger.error("Failed to load private key: %s", str(e))
    raise

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
    }
}