from django.core.management.base import BaseCommand
from apps.chat.models import KnowledgeChunk
from apps.chat.embedding_service import embed_document
from apps.chat.knowledge_base import TAWFIR_KNOWLEDGE


class Command(BaseCommand):
    help = "Embed all knowledge chunks and store them in PostgreSQL with pgvector."

    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting existing knowledge base...")
        KnowledgeChunk.objects.all().delete()

        self.stdout.write(f"Indexing {len(TAWFIR_KNOWLEDGE)} chunks...")

        for item in TAWFIR_KNOWLEDGE:
            embedding = embed_document(item["content"])

            KnowledgeChunk.objects.create(
                topic_id=item["topic_id"],
                content=item["content"],
                relevant_for=item["relevant_for"],
                embedding=embedding,
            )
            self.stdout.write(f"  ✓ {item['topic_id']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nKnowledge base ready: {len(TAWFIR_KNOWLEDGE)} chunks indexed."
        ))
