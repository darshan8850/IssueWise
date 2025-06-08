import asyncio
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from llama_index.core import VectorStoreIndex, Document, Settings, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.mistralai import MistralAIEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.anthropic import AnthropicEmbedding
from llama_index.llms.mistralai import MistralAI
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from config import AVAILABLE_MODELS
from tools.utils import fetch_repo_files, fetch_file_content


INCLUDE_FILE_EXTENSIONS = {".py", ".js", ".ts", ".json", ".md", ".txt"}

def get_embedding_model(model_type: str):
    """Get the appropriate embedding model based on the model type."""
    model_config = AVAILABLE_MODELS.get(model_type)
    if not model_config or not model_config["api_key"]:
        raise ValueError(f"Invalid model type or missing API key for {model_type}")
    
    if model_type == "mistral":
        return MistralAIEmbedding(model_name="codestral-embed", api_key=model_config["api_key"])
    elif model_type == "openai":
        return OpenAIEmbedding(model="text-embedding-3-small", api_key=model_config["api_key"])
    elif model_type == "claude":
        return AnthropicEmbedding(model="claude-3-opus-20240229", api_key=model_config["api_key"])
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

def get_llm_model(model_type: str):
    """Get the appropriate LLM model based on the model type."""
    model_config = AVAILABLE_MODELS.get(model_type)
    if not model_config or not model_config["api_key"]:
        raise ValueError(f"Invalid model type or missing API key for {model_type}")
    
    if model_type == "mistral":
        return MistralAI(model="codestral-latest", api_key=model_config["api_key"])
    elif model_type == "openai":
        return OpenAI(model="gpt-4-turbo-preview", api_key=model_config["api_key"])
    elif model_type == "claude":
        return Anthropic(model="claude-3-opus-20240229", api_key=model_config["api_key"])
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

def safe_normalize(vec: np.ndarray) -> np.ndarray:
    vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    norm = np.linalg.norm(vec)
    if norm == 0 or np.isnan(norm) or np.isinf(norm):
        return None
    return vec / norm

def select_relevant_files_semantic(issue_description: str, file_paths: List[str], model_type: str = "mistral") -> List[str]:
    embed_model = get_embedding_model(model_type)

    issue_embedding = np.array(embed_model.get_text_embedding(issue_description), dtype=np.float64)
    issue_embedding = safe_normalize(issue_embedding)
    if issue_embedding is None:
        print("[Warning] Issue description embedding invalid (zero or NaN norm). Returning empty list.")
        return []

    scored_files = []

    for path in file_paths:
        try:
            file_embedding = np.array(embed_model.get_text_embedding(path), dtype=np.float64)
            file_embedding = safe_normalize(file_embedding)
            if file_embedding is None:
                print(f"[Warning] Skipping {path} due to zero or invalid embedding norm.")
                continue
            
            with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
                score = cosine_similarity([issue_embedding], [file_embedding])[0][0]

            if np.isnan(score) or np.isinf(score):
                print(f"[Warning] Skipping {path} due to invalid similarity score.")
                continue

            scored_files.append((path, score))
        except Exception as e:
            print(f"[Warning] Skipping {path} due to error: {e}")

    top_files = [f[0] for f in sorted(scored_files, key=lambda x: x[1], reverse=True)[:2]]

    if "README.md" in file_paths:
        if "README.md" not in top_files:
            top_files.insert(0, "README.md")

    return top_files

async def async_retry_on_429(func, *args, max_retries=3, delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            status = getattr(e, 'response', None) and getattr(e.response, 'status_code', None)
            if status == 429:
                print(f"[Retry] Rate limit hit while calling {func.__name__}. Attempt {attempt+1}/{max_retries}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise

async def build_repo_index(owner: str, repo: str, ref: str = "main", issue_description: str = "", model_type: str = "mistral") -> VectorStoreIndex:
    embed_model = get_embedding_model(model_type)
    print(f"[Indexing] Starting to index repository: {owner}/{repo} at ref {ref}...")

    file_paths = await async_retry_on_429(fetch_repo_files, owner, repo, ref)

    if issue_description:
        file_paths = select_relevant_files_semantic(issue_description, file_paths, model_type)

    documents = []

    for path in file_paths:
        _, ext = os.path.splitext(path)
        if ext.lower() not in INCLUDE_FILE_EXTENSIONS:
            continue

        try:
            content = await async_retry_on_429(fetch_file_content, owner, repo, path, ref)
            documents.append(Document(text=content, metadata={"file_path": path}))
            print(f"[Indexing] Added file: {path}")
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[Warning] Skipping file {path} due to error: {e}")

    try:
        index = await async_retry_on_429(VectorStoreIndex.from_documents, documents, embed_model=embed_model)
    except Exception as e:
        print(f"[Error] Failed to build index due to: {e}")
        raise

    print(f"[Indexing] Finished indexing {len(documents)} files.")
    return index


async def retrieve_context(owner: str, repo: str, ref: str, issue_description: str, model_type: str = "mistral") -> List[str]:
    index = await build_repo_index(owner, repo, ref, issue_description, model_type)
    
    # Set the LLM and embedding model based on the selected model type
    Settings.llm = get_llm_model(model_type)
    Settings.embed_model = get_embedding_model(model_type)

    retriever = index.as_retriever(similarity_top_k=3)

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=get_response_synthesizer(),
        node_postprocessors=[
            SimilarityPostprocessor(similarity_top_k=3, similarity_cutoff=0.75)
        ],
    )

    query = (
        f"Please give relevant information from the codebase that highly matches the keywords of this issue and is useful for solving or understanding this issue: {issue_description}\n"
        "STRICT RULES:\n"
        "- ONLY use information available in the retriever context.\n"
        "- DO NOT generate or assume any information outside the given context.\n"
        f"- ONLY include context that is highly relevant and clearly useful for understanding or solving this issue: {issue_description}\n"
        "- DO NOT include generic, loosely related, or unrelated content.\n"
    )

    response = await asyncio.to_thread(query_engine.query, query)

    print(response)
    return response