# support/embedding_service.py

import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"
# Keep the existing 768-dimensional pgvector schema.


def embed_document(text: str) -> list[float]:
    """
    Used when indexing knowledge chunks into the database.
    Task type 'retrieval_document' tells the model this text
    will be the thing being searched for, not the query.
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    return result["embedding"]


def embed_user_query(text: str) -> list[float]:
    """
    Used when a user sends a message.
    Task type 'retrieval_query' tells the model this is the
    search question, optimising it to match document vectors.
    Using the correct task type meaningfully improves retrieval quality.
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=768,
    )
    return result["embedding"]
