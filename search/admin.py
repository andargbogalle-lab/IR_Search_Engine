"""
Django Admin configuration for the IR Search Engine.
"""
from django.contrib import admin
from .models import Document, IndexEntry, EvaluationResult
from .ir_engine import Indexer
import json

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'status', 'owner', 'is_indexed', 'word_count', 'created_at')
    list_filter = ('status', 'language', 'is_indexed')
    search_fields = ('title', 'raw_text')
    actions = ['approve_and_index', 'mark_as_unindexed']

    @admin.action(description='Approve and Index selected documents')
    def approve_and_index(self, request, queryset):
        queryset.update(status='approved')
        
        # Re-run indexing for all approved documents
        all_docs = Document.objects.filter(status='approved')
        indexer = Indexer()
        result = indexer.build_index(all_docs)
        
        index_data = result['index']
        doc_lengths = result['doc_lengths']
        
        # Update word counts
        for doc_id_str, length in doc_lengths.items():
            Document.objects.filter(id=int(doc_id_str)).update(word_count=length, is_indexed=True)
            
        # Update inverted index in DB
        IndexEntry.objects.all().delete()
        entries_to_create = [
            IndexEntry(term=term, doc_frequency=len(postings), postings_json=json.dumps(postings))
            for term, postings in index_data.items()
        ]
        
        # Batch save
        for i in range(0, len(entries_to_create), 1000):
            IndexEntry.objects.bulk_create(entries_to_create[i:i+1000])
            
        self.message_user(request, f"Successfully approved and indexed {queryset.count()} documents.")

    @admin.action(description='Mark selected documents as unindexed')
    def mark_as_unindexed(self, request, queryset):
        queryset.update(is_indexed=False)

@admin.register(IndexEntry)
class IndexEntryAdmin(admin.ModelAdmin):
    list_display = ('term', 'doc_frequency')
    search_fields = ('term',)

@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'model_used', 'precision_at_5', 'recall', 'created_at')
    list_filter = ('model_used',)
    search_fields = ('query_text',)
