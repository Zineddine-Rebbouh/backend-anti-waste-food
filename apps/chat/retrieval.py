# support/retrieval.py

from pgvector.django import CosineDistance
from apps.chat.models import KnowledgeChunk
from apps.chat.embedding_service import embed_user_query


def retrieve_relevant_chunks(
    user_message: str,
    user_type: str,
    top_k: int = 4,
    min_similarity: float = 0.30,
) -> list[dict]:
    """
    Given a user's message, find the most semantically relevant
    knowledge chunks from the database.

    Parameters:
        user_message  — the raw text the user sent
        user_type     — 'consumer', 'merchant', or 'charity'
                        Used to filter chunks by relevance
        top_k         — maximum number of chunks to return
        min_similarity — chunks below this similarity score are excluded
                        Prevents injecting irrelevant information when
                        the user's question has no good match

    Returns a list of dicts with 'topic_id' and 'content'.
    """

    # Step 1: Convert the user's question to a vector.
    # This is a single API call to Google and takes ~0.1 seconds.
    query_vector = embed_user_query(user_message)

    # Step 2: Search PostgreSQL using cosine distance.
    # CosineDistance returns a value between 0 (identical) and 2 (opposite).
    # We convert: similarity = 1 - distance.
    # Only chunks relevant to this user type are considered.
    results = (
        KnowledgeChunk.objects
        .filter(relevant_for__contains=user_type)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lt=(1 - min_similarity))   # Enforce minimum relevance
        .order_by("distance")                         # Closest first
        [:top_k]
    )

    return [
        {"topic_id": chunk.topic_id, "content": chunk.content}
        for chunk in results
    ]
