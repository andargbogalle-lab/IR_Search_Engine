"""
Django models for the IR Search Engine.
Defines Document, IndexEntry, and EvaluationResult models.
"""
from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
import json


class Document(models.Model):
    """Represents a document in the corpus."""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('am', 'Amharic'),
        ('mixed', 'Mixed'),
    ]

    title = models.CharField(max_length=500, db_index=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en', db_index=True)
    raw_text = models.TextField()
    source_url = models.URLField(blank=True, null=True)
    pub_date = models.DateField(blank=True, null=True)
    file_path = models.CharField(max_length=1000, blank=True, null=True)
    is_indexed = models.BooleanField(default=False, db_index=True)
    word_count = models.IntegerField(default=0)
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    owner = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    
    # New fields for enhanced functionality
    view_count = models.IntegerField(default=0)
    search_count = models.IntegerField(default=0)  # How many times this doc appeared in search results
    last_indexed = models.DateTimeField(null=True, blank=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    checksum = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 checksum for duplicate detection")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_indexed']),
            models.Index(fields=['language', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.language.upper()}] {self.title}"

    def snippet(self, length=200):
        """Return a short snippet of the document text."""
        if len(self.raw_text) <= length:
            return self.raw_text
        return self.raw_text[:length] + "..."
    
    def increment_view_count(self):
        """Increment view count atomically."""
        Document.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)
        self.refresh_from_db()
    
    def increment_search_count(self):
        """Increment search result appearance count."""
        Document.objects.filter(pk=self.pk).update(search_count=models.F('search_count') + 1)
        self.refresh_from_db()


class IndexEntry(models.Model):
    """Inverted index entry mapping a term to documents."""
    term = models.CharField(max_length=200, unique=True, db_index=True)
    doc_frequency = models.IntegerField(default=0)  # How many docs contain this term
    postings_json = models.TextField(default='{}')   # JSON: {doc_id: {tf: x, tfidf: y, positions: [...]}}
    
    # New fields for better search
    total_term_frequency = models.IntegerField(default=0)  # Total occurrences across all docs
    idf_score = models.FloatField(default=0.0)  # Pre-calculated IDF

    class Meta:
        verbose_name_plural = "Index Entries"
        ordering = ['term']
        indexes = [
            models.Index(fields=['term']),
            models.Index(fields=['doc_frequency']),
        ]

    def __str__(self):
        return f"{self.term} (df={self.doc_frequency})"

    def get_postings(self):
        """Return postings as a Python dictionary."""
        return json.loads(self.postings_json)

    def set_postings(self, postings_dict):
        """Set postings from a Python dictionary."""
        self.postings_json = json.dumps(postings_dict)


class EvaluationResult(models.Model):
    """Stores evaluation metrics for test queries."""
    MODEL_CHOICES = [
        ('vsm', 'Vector Space Model (TF-IDF)'),
        ('bm25', 'BM25'),
    ]

    query_text = models.CharField(max_length=500)
    model_used = models.CharField(max_length=10, choices=MODEL_CHOICES)
    precision_at_5 = models.FloatField(default=0.0)
    recall = models.FloatField(default=0.0)
    f1_score = models.FloatField(default=0.0)  # New field
    mean_average_precision = models.FloatField(default=0.0)  # New field
    results_json = models.TextField(default='[]')  # JSON list of returned doc IDs
    relevant_docs_json = models.TextField(default='[]')  # JSON list of relevant doc IDs
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.model_used.upper()}] '{self.query_text}' P@5={self.precision_at_5:.2f}"

    def get_results(self):
        return json.loads(self.results_json)

    def get_relevant_docs(self):
        return json.loads(self.relevant_docs_json)


class SearchHistory(models.Model):
    """Stores search history for authenticated users."""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='search_history')
    query_text = models.CharField(max_length=500, db_index=True)
    model_used = models.CharField(max_length=10, default='vsm')
    language = models.CharField(max_length=10, default='en')
    results_count = models.IntegerField(default=0)
    execution_time = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Search Histories"
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['query_text']),
        ]

    def __str__(self):
        return f"{self.user.username} searched for '{self.query_text}' on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class QuerySuggestion(models.Model):
    """Stores popular queries for autocomplete suggestions."""
    query_text = models.CharField(max_length=500, unique=True, db_index=True)
    search_count = models.IntegerField(default=1)
    last_searched = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-search_count', '-last_searched']
        indexes = [
            models.Index(fields=['-search_count', '-last_searched']),
        ]
    
    def __str__(self):
        return f"{self.query_text} ({self.search_count} searches)"


class SpellCorrection(models.Model):
    """Stores spell correction mappings."""
    misspelled = models.CharField(max_length=200, unique=True, db_index=True)
    corrected = models.CharField(max_length=200)
    frequency = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['-frequency']
    
    def __str__(self):
        return f"{self.misspelled} → {self.corrected}"

