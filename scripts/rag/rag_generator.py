#!/usr/bin/env python3
"""
rag_generator.py

Provides functions to generate a structured JSON response from an LLM based on a query
and retrieved context, ensuring answers always include citations and showing chunk identifiers.
"""

import os
import sys
import warnings
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(dotenv_path="/home/jonathan_morse/ragui/.env")

# --- OpenAI Client Setup ---
try:
    from openai import OpenAI, RateLimitError, APIError
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    OPENAI_AVAILABLE = True
    print("✅ OpenAI client initialized successfully.")
except ImportError:
    warnings.warn("⚠️ Install OpenAI library: pip install openai")
    OPENAI_AVAILABLE = False
    client = None
except ValueError as e:
    warnings.warn(f"⚠️ OpenAI API key error: {e}")
    OPENAI_AVAILABLE = False
    client = None

# --- Configuration ---
LLM_MODEL = "gpt-4o-2024-08-06"  # ensure model supports structured outputs
MAX_TOKENS_RESPONSE = 500
TEMPERATURE = 0.5

# --- JSON Schema for Structured Response Including Chunk IDs ---
rag_response_schema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": { "type": "string" },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": { "type": "string" },
                    "source":   { "type": "string" }
                },
                "required": ["chunk_id", "source"],
                "additionalProperties": False
            }
        }
    },
    "required": ["answer", "sources"],
    "additionalProperties": False
}

# --- Core Generation Function ---

def generate_response_from_context(query: str, context_block: str, chat_history: List[Dict[str, str]] = []) -> Dict[str, Any]:
    """
    Generates a structured JSON response using an LLM based on the user query
    and retrieved context. The output always includes 'answer' and a list of
    'sources', each with a 'chunk_id' and 'source' path.

    Returns:
        A dict with keys:
          - 'answer': str
          - 'sources': List[Dict[str, str]]
    """
    print("\n--- Starting Structured Generation ---")

    if not OPENAI_AVAILABLE or client is None:
        return {"answer": "Error: OpenAI client unavailable.", "sources": []}

    if not context_block.strip():
        return {"answer": "No context available to answer the query.", "sources": []}

    # # Debug: show the exact context being passed
    # print("--- Context Being Sent to LLM ---")
    # print(context_block)
    # print("--- End of Context ---")

    # Prepare messages with schema instructions
    system_message = (
        "You are an expert assistant. Answer only based on the provided context chunks. "
        "Return a JSON object with 'answer' (concise response) and 'sources', an array of objects each containing "
        "'chunk_id' (identifier of the chunk) and 'source' (filepath or document ID)."
    )
    user_prompt = f"""
User Query: "{query}"

Context Chunks:
{context_block}

Return JSON with two keys:
1. answer: Your direct response.
2. sources: [ {{chunk_id: "id", source: "path"}}, ... ]

If no answer is found, set 'answer' to a note indicating none and 'sources' to [].
"""

    # # Print input for debugging
    # print("\n--- Sending Input to LLM ---")
    # print(f"System Message:\n{system_message}\n")
    # print(f"User Prompt:\n{user_prompt}\n")
    # print("--- End of LLM Input ---")

    try:
        response = client.responses.create(
            model=LLM_MODEL,
            input=[
                {"role": "system", "content": system_message},
                *chat_history,
                {"role": "user",   "content": user_prompt}
            ],
            text={
                "format": {
                    "type":   "json_schema",
                    "name":   "rag_response",
                    "schema": rag_response_schema,
                    "strict": True
                }
            },
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS_RESPONSE
        )
        raw = response.output_text
        structured = json.loads(raw)
        print("   ✅ Structured response parsed.")
        return structured

    except RateLimitError:
        return {"answer": "Error: Rate limit exceeded.", "sources": []}
    except APIError as e:
        return {"answer": f"API Error: {e}", "sources": []}
    except Exception as e:
        return {"answer": f"Unexpected error: {e}", "sources": []}

# --- Example Usage ---
if __name__ == "__main__":
    print("Running structured RAG Generator Test...")
    try:
        from rag_retriever import retrieve_and_format_context
        RETRIEVER_AVAILABLE = True
    except ImportError:
        RETRIEVER_AVAILABLE = False
        def retrieve_and_format_context(q, num_chunks=3):
            return "", []

    test_query = "What does ammonia do in the CHA synthesis reaction?"
    ctx_block, sources = retrieve_and_format_context(test_query, num_chunks=3)
    result = generate_response_from_context(test_query, ctx_block)
    print(json.dumps(result, indent=2))
