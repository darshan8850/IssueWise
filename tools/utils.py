import asyncio
import base64
from datetime import datetime, timezone, timedelta
import jwt
import threading
import time
from typing import List, Optional, Dict, Any
import requests
import logging
from config import APP_ID, APP_PRIVATE_KEY

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

installation_tokens = {}
token_lock = threading.Lock()


def validate_app_configuration() -> Dict[str, Any]:
    """Validate the GitHub App configuration and return app details."""
    try:
        jwt_token = generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get("https://api.github.com/app", headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to validate app configuration: {response.status_code} {response.text}")
        
        app_data = response.json()
        logger.info("GitHub App validated successfully: %s", app_data.get("name"))
        return app_data
    except Exception as e:
        logger.error("Failed to validate GitHub App configuration: %s", str(e))
        raise


def format_private_key(key: str) -> str:
    """Format the private key properly for JWT signing."""
    if not key:
        raise ValueError("Private key is empty")
    
    # Remove any existing newlines and whitespace
    key = key.strip()
    
    # Remove any existing headers/footers to start fresh
    key = key.replace("-----BEGIN RSA PRIVATE KEY-----", "")
    key = key.replace("-----END RSA PRIVATE KEY-----", "")
    key = key.strip()
    
    # Add proper headers and footers
    key = "-----BEGIN RSA PRIVATE KEY-----\n" + key + "\n-----END RSA PRIVATE KEY-----"
    
    # Ensure proper line breaks
    key = key.replace("\\n", "\n")
    
    # Add line breaks every 64 characters in the key body
    lines = key.split("\n")
    formatted_lines = []
    for line in lines:
        if line.startswith("-----"):
            formatted_lines.append(line)
        else:
            # Remove any spaces from the key content
            line = line.replace(" ", "")
            # Split the line into 64-character chunks
            chunks = [line[i:i+64] for i in range(0, len(line), 64)]
            formatted_lines.extend(chunks)
    
    formatted_key = "\n".join(formatted_lines)
    logger.debug("Formatted private key (first 50 chars): %s...", formatted_key[:50])
    return formatted_key


def generate_jwt():
    """Generate a JWT signed with GitHub App private key."""
    try:
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + (10 * 60),
            "iss": APP_ID,
        }
        encoded_jwt = jwt.encode(payload, APP_PRIVATE_KEY, algorithm="RS256")
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to generate JWT: %s", str(e))
        raise


def github_request(method, url, headers=None, **kwargs):
    if headers is None:
        jwt_token = generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }
    while True:
        response = requests.request(method, url, headers=headers, **kwargs)
        
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")

        if remaining is None or reset_time is None:
            return response
        
        remaining = int(remaining)
        reset_time = int(reset_time)

        logger.debug(f"[GitHub] Remaining: {remaining}, Reset: {reset_time}")

        if response.status_code == 403 and "rate limit" in response.text.lower():
            wait = reset_time - int(time.time()) + 5
            logger.warning(f"Hit rate limit. Sleeping for {wait} seconds.")
            time.sleep(max(wait, 0))
            continue
        if remaining <= 2:
            wait = reset_time - int(time.time()) + 5
            logger.warning(f"Approaching rate limit ({remaining} left). Sleeping for {wait} seconds.")
            time.sleep(max(wait, 0))
            continue

        return response


def get_app_installations():
    """Get all installations of the GitHub App."""
    url = "https://api.github.com/app/installations"
    response = github_request("GET", url)
    if response.status_code != 200:
        raise Exception(f"Failed to get app installations: {response.status_code} {response.text}")
    return response.json()


def get_installation_id(owner: str, repo: str) -> Optional[int]:
    """Fetch the installation ID for the app on a repo."""
    # First validate app configuration
    try:
        app_data = validate_app_configuration()
        logger.info("Using GitHub App: %s (ID: %s)", app_data.get("name"), app_data.get("id"))
    except Exception as e:
        logger.error("GitHub App configuration validation failed: %s", str(e))
        raise Exception(
            "GitHub App is not properly configured. Please check:\n"
            "1. APP_ID is set correctly in your .env file\n"
            "2. APP_PRIVATE_KEY is valid and properly formatted\n"
            "3. The GitHub App exists and is active"
        )

    # Try to get repository installation
    url = f"https://api.github.com/repos/{owner}/{repo}/installation"
    response = github_request("GET", url)
    
    if response.status_code == 200:
        data = response.json()
        return data["id"]
    elif response.status_code == 404:
        # If not found, check if the app is installed on the organization
        org_url = f"https://api.github.com/orgs/{owner}/installation"
        org_response = github_request("GET", org_url)
        
        if org_response.status_code == 200:
            data = org_response.json()
            return data["id"]
        else:
            # Get all installations to help debug
            try:
                installations = get_app_installations()
                installation_urls = [
                    inst.get("html_url") for inst in installations
                    if inst.get("html_url")
                ]
                
                error_msg = (
                    f"GitHub App is not installed on {owner}/{repo}.\n\n"
                    "To fix this:\n"
                    "1. Go to your GitHub App settings\n"
                    "2. Click 'Install App'\n"
                    "3. Select the organization or repository\n"
                    "4. Grant the necessary permissions\n\n"
                )
                
                if installation_urls:
                    error_msg += "Current installations:\n" + "\n".join(f"- {url}" for url in installation_urls)
                else:
                    error_msg += "No installations found. Please install the app first."
                
                logger.error(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                logger.error("Failed to get installations: %s", str(e))
                raise Exception(
                    f"GitHub App is not installed on {owner}/{repo}. "
                    "Please install the app on the repository or organization. "
                    "Visit your GitHub App settings to get the installation URL."
                )
    else:
        raise Exception(f"Failed to get installation ID for {owner}/{repo}: {response.status_code} {response.text}")


def get_installation_token(installation_id):
    """Return a valid installation token, fetch new if expired or missing."""
    with token_lock:
        token_info = installation_tokens.get(installation_id)
        if token_info and token_info["expires_at"] > datetime.now(timezone.utc) + timedelta(seconds=30):
            return token_info["token"]

        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        response = github_request("POST", url)
        if response.status_code != 201:
            raise Exception(f"Failed to fetch installation token: {response.status_code} {response.text}")

        token_data = response.json()
        token = token_data["token"]
        expires_at = datetime.strptime(token_data["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

        installation_tokens[installation_id] = {"token": token, "expires_at": expires_at}
        return token


async def fetch_repo_files(owner: str, repo: str, ref: str = "main") -> List[str]:
    """
    Lists all files in the repository by recursively fetching the Git tree from GitHub API.
    Returns a list of file paths.
    """
    installation_id = get_installation_id(owner, repo)
    token = get_installation_token(installation_id)
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = await asyncio.to_thread(github_request, "GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to list repository files: {response.status_code} {response.text}")

    tree = response.json().get("tree", [])
    file_paths = [item["path"] for item in tree if item["type"] == "blob"]
    return file_paths


async def fetch_file_content(owner: str, repo: str, path: str, ref: str = "main") -> str:
    """
    Fetches the content of a file from the GitHub repository.
    """
    installation_id = get_installation_id(owner, repo)
    token = await asyncio.to_thread(get_installation_token, installation_id)

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = await asyncio.to_thread(github_request, "GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch file content {path}: {response.status_code} {response.text}")

    content_json = response.json()
    content = base64.b64decode(content_json["content"]).decode("utf-8", errors="ignore")
    return content
