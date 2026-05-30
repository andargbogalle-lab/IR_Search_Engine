from django.core.management.base import BaseCommand
from search.models import Document, IndexEntry
from search.ir_engine.indexer import Indexer
import json

class Command(BaseCommand):
    help = 'Builds the inverted index and calculates TF-IDF for all unindexed documents'

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching unindexed documents...")
        unindexed_docs = Document.objects.filter(is_indexed=False)
        
        if not unindexed_docs.exists():
            self.stdout.write(self.style.SUCCESS("No new documents to index."))
            return
            
        doc_count = unindexed_docs.count()
        self.stdout.write(f"Found {doc_count} unindexed documents. Starting indexing...")
        
        # Build index for new docs
        # Note: In a production system, you'd merge the new index with the existing one
        # and re-calculate IDF across the entire corpus.
        # For simplicity here, we're going to re-index EVERYTHING to keep IDF accurate.
        all_docs = Document.objects.all()
        
        indexer = Indexer()
        result = indexer.build_index(all_docs)
        index_data = result['index']
        doc_lengths = result['doc_lengths']
        
        self.stdout.write("Saving index to database...")
        
        # Update word counts for documents
        for doc_id_str, length in doc_lengths.items():
            Document.objects.filter(id=int(doc_id_str)).update(word_count=length, is_indexed=True)
            
        # Update/Create index entries
        # Clear existing index to avoid stale data
        IndexEntry.objects.all().delete()
        
        entries_to_create = []
        for term, postings in index_data.items():
            entry = IndexEntry(
                term=term,
                doc_frequency=len(postings),
                postings_json=json.dumps(postings)
            )
            entries_to_create.append(entry)
            
            # Batch save to avoid too many DB queries
            if len(entries_to_create) >= 1000:
                IndexEntry.objects.bulk_create(entries_to_create)
                entries_to_create = []
                
        if entries_to_create:
            IndexEntry.objects.bulk_create(entries_to_create)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully indexed {len(all_docs)} documents with {len(index_data)} unique terms."))
