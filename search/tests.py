"""
Comprehensive test suite for the IR Search Engine.
Run with: python manage.py test
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from search.models import Document, IndexEntry, SearchHistory, QuerySuggestion
from search.ir_engine.preprocessor import Preprocessor
from search.ir_engine.indexer import Indexer
from search.ir_engine.vsm import VSM
from search.ir_engine.bm25 import BM25
from search.ir_engine.spell_checker import SpellChecker
import json


class PreprocessorTestCase(TestCase):
    """Test text preprocessing functionality."""
    
    def setUp(self):
        self.preprocessor = Preprocessor()
    
    def test_english_tokenization(self):
        """Test English text tokenization."""
        text = "The quick brown fox jumps over the lazy dog."
        tokens = self.preprocessor.tokenize(text, language='en')
        self.assertIn('quick', tokens)
        self.assertIn('brown', tokens)
        self.assertIn('fox', tokens)
    
    def test_stopword_removal(self):
        """Test stopword removal."""
        words = ['the', 'quick', 'brown', 'fox', 'and', 'dog']
        filtered = self.preprocessor.remove_stopwords(words, language='en')
        self.assertNotIn('the', filtered)
        self.assertNotIn('and', filtered)
        self.assertIn('quick', filtered)
        self.assertIn('fox', filtered)
    
    def test_stemming(self):
        """Test word stemming."""
        words = ['running', 'runs', 'ran', 'runner']
        stemmed = self.preprocessor.stem(words, language='en')
        # All should stem to similar root
        self.assertTrue(len(set(stemmed)) < len(words))
    
    def test_full_pipeline(self):
        """Test complete preprocessing pipeline."""
        text = "The running dogs are jumping over fences."
        processed = self.preprocessor.process_text(text, language='en')
        self.assertIsInstance(processed, list)
        self.assertTrue(len(processed) > 0)
        self.assertNotIn('the', processed)  # Stopword removed
    
    def test_amharic_tokenization(self):
        """Test Amharic text tokenization."""
        text = "ሰላም ዓለም እንዴት ነህ"
        tokens = self.preprocessor.tokenize(text, language='am')
        self.assertTrue(len(tokens) > 0)
        self.assertIn('ሰላም', tokens)


class IndexerTestCase(TestCase):
    """Test indexing functionality."""
    
    def setUp(self):
        self.indexer = Indexer()
        # Create test documents
        self.doc1 = Document.objects.create(
            title="Agriculture Document",
            language='en',
            raw_text="Wheat farming is important for agriculture. Wheat grows in fields.",
            status='approved'
        )
        self.doc2 = Document.objects.create(
            title="Technology Document",
            language='en',
            raw_text="Computer science and technology are advancing rapidly.",
            status='approved'
        )
    
    def test_index_building(self):
        """Test inverted index construction."""
        docs = Document.objects.filter(status='approved')
        result = self.indexer.build_index(docs)
        
        self.assertIn('index', result)
        self.assertIn('doc_lengths', result)
        self.assertIn('total_docs', result)
        self.assertEqual(result['total_docs'], 2)
    
    def test_term_frequency(self):
        """Test term frequency calculation."""
        docs = Document.objects.filter(status='approved')
        result = self.indexer.build_index(docs)
        index = result['index']
        
        # 'wheat' appears twice in doc1
        if 'wheat' in index:
            doc1_posting = index['wheat'].get(str(self.doc1.id))
            if doc1_posting:
                self.assertEqual(doc1_posting['tf'], 2)
    
    def test_tfidf_calculation(self):
        """Test TF-IDF weight calculation."""
        docs = Document.objects.filter(status='approved')
        result = self.indexer.build_index(docs)
        index = result['index']
        
        # Check that TF-IDF weights are calculated
        for term, postings in index.items():
            for doc_id, data in postings.items():
                self.assertIn('tfidf', data)
                self.assertIsInstance(data['tfidf'], (int, float))


class SearchEngineTestCase(TestCase):
    """Test search engine functionality."""
    
    def setUp(self):
        # Create test documents
        self.doc1 = Document.objects.create(
            title="Wheat Farming Guide",
            language='en',
            raw_text="Wheat is a cereal grain. Wheat farming requires proper soil and climate. Wheat production is important.",
            status='approved',
            is_indexed=True,
            word_count=15
        )
        self.doc2 = Document.objects.create(
            title="Rice Cultivation",
            language='en',
            raw_text="Rice is a staple food. Rice cultivation needs water. Rice paddies are common in Asia.",
            status='approved',
            is_indexed=True,
            word_count=14
        )
        
        # Build index
        indexer = Indexer()
        result = indexer.build_index(Document.objects.filter(status='approved'))
        
        # Save to database
        for term, postings in result['index'].items():
            IndexEntry.objects.create(
                term=term,
                doc_frequency=len(postings),
                postings_json=json.dumps(postings)
            )
    
    def test_vsm_search(self):
        """Test Vector Space Model search."""
        vsm = VSM()
        results = vsm.search("wheat farming", language='en', top_k=10)
        
        self.assertIsInstance(results, list)
        if results:
            doc_id, score = results[0]
            self.assertEqual(doc_id, self.doc1.id)
            self.assertGreater(score, 0)
    
    def test_bm25_search(self):
        """Test BM25 search."""
        bm25 = BM25()
        results = bm25.search("wheat farming", language='en', top_k=10)
        
        self.assertIsInstance(results, list)
        if results:
            doc_id, score = results[0]
            self.assertGreater(score, 0)
    
    def test_empty_query(self):
        """Test handling of empty queries."""
        vsm = VSM()
        results = vsm.search("", language='en', top_k=10)
        self.assertEqual(len(results), 0)
    
    def test_no_results(self):
        """Test query with no matching documents."""
        vsm = VSM()
        results = vsm.search("quantum physics", language='en', top_k=10)
        self.assertEqual(len(results), 0)


class SpellCheckerTestCase(TestCase):
    """Test spell checking functionality."""
    
    def setUp(self):
        # Create index entries for vocabulary
        IndexEntry.objects.create(term='agriculture', doc_frequency=10)
        IndexEntry.objects.create(term='farming', doc_frequency=8)
        IndexEntry.objects.create(term='wheat', doc_frequency=15)
        
        self.spell_checker = SpellChecker()
        self.spell_checker.load_vocabulary()
    
    def test_correct_spelling(self):
        """Test correction of misspelled words."""
        # Test with known vocabulary
        corrected = self.spell_checker.correct('agricultur')
        self.assertIn(corrected, ['agriculture', 'agricultur'])
    
    def test_already_correct(self):
        """Test that correct words are unchanged."""
        corrected = self.spell_checker.correct('wheat')
        self.assertEqual(corrected, 'wheat')


class ViewsTestCase(TestCase):
    """Test view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpass123',
            is_staff=True
        )
    
    def test_home_view(self):
        """Test home page loads."""
        response = self.client.get(reverse('search:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search')
    
    def test_search_view(self):
        """Test search results page."""
        response = self.client.get(reverse('search:results'), {'q': 'test query'})
        self.assertEqual(response.status_code, 200)
    
    def test_upload_view_requires_login(self):
        """Test upload page requires authentication."""
        response = self.client.get(reverse('search:upload'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_upload_view_authenticated(self):
        """Test upload page for authenticated users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('search:upload'))
        self.assertEqual(response.status_code, 200)
    
    def test_document_upload(self):
        """Test document upload functionality."""
        self.client.login(username='staffuser', password='staffpass123')
        
        file_content = b"This is a test document about agriculture and farming."
        uploaded_file = SimpleUploadedFile("test.txt", file_content, content_type="text/plain")
        
        response = self.client.post(reverse('search:upload'), {
            'title': 'Test Document',
            'language': 'en',
            'document_file': uploaded_file
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Document.objects.filter(title='Test Document').exists())
    
    def test_search_history(self):
        """Test search history tracking."""
        self.client.login(username='testuser', password='testpass123')
        
        # Perform a search
        self.client.get(reverse('search:results'), {'q': 'test query'})
        
        # Check history was created
        self.assertTrue(SearchHistory.objects.filter(
            user=self.user,
            query_text='test query'
        ).exists())
    
    def test_document_detail_view(self):
        """Test document detail page."""
        doc = Document.objects.create(
            title="Test Doc",
            language='en',
            raw_text="Test content",
            status='approved'
        )
        
        response = self.client.get(reverse('search:document_detail', args=[doc.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Doc")
    
    def test_autocomplete(self):
        """Test autocomplete suggestions."""
        QuerySuggestion.objects.create(query_text='agriculture', search_count=10)
        QuerySuggestion.objects.create(query_text='farming', search_count=5)
        
        response = self.client.get(reverse('search:autocomplete'), {'q': 'agr'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('suggestions', data)


class ModelTestCase(TestCase):
    """Test model functionality."""
    
    def test_document_creation(self):
        """Test document model creation."""
        doc = Document.objects.create(
            title="Test Document",
            language='en',
            raw_text="This is test content.",
            status='pending'
        )
        
        self.assertEqual(doc.title, "Test Document")
        self.assertEqual(doc.language, 'en')
        self.assertEqual(doc.status, 'pending')
        self.assertFalse(doc.is_indexed)
    
    def test_document_snippet(self):
        """Test document snippet generation."""
        long_text = "A" * 300
        doc = Document.objects.create(
            title="Long Doc",
            language='en',
            raw_text=long_text,
            status='approved'
        )
        
        snippet = doc.snippet(length=200)
        self.assertLessEqual(len(snippet), 203)  # 200 + "..."
    
    def test_index_entry_postings(self):
        """Test index entry postings serialization."""
        postings = {
            '1': {'tf': 3, 'tfidf': 0.5, 'positions': [0, 5, 10]},
            '2': {'tf': 1, 'tfidf': 0.2, 'positions': [3]}
        }
        
        entry = IndexEntry.objects.create(
            term='test',
            doc_frequency=2
        )
        entry.set_postings(postings)
        entry.save()
        
        retrieved_postings = entry.get_postings()
        self.assertEqual(retrieved_postings, postings)
    
    def test_query_suggestion_creation(self):
        """Test query suggestion model."""
        suggestion = QuerySuggestion.objects.create(
            query_text='test query',
            search_count=5
        )
        
        self.assertEqual(suggestion.query_text, 'test query')
        self.assertEqual(suggestion.search_count, 5)


class IntegrationTestCase(TestCase):
    """Integration tests for complete workflows."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
    
    def test_complete_search_workflow(self):
        """Test complete search workflow from upload to search."""
        # Login
        self.client.login(username='testuser', password='testpass123')
        
        # Upload document
        file_content = b"Wheat farming is essential for food security. Wheat grows in temperate climates."
        uploaded_file = SimpleUploadedFile("wheat.txt", file_content, content_type="text/plain")
        
        response = self.client.post(reverse('search:upload'), {
            'title': 'Wheat Farming Guide',
            'language': 'en',
            'document_file': uploaded_file
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify document was created
        doc = Document.objects.get(title='Wheat Farming Guide')
        self.assertEqual(doc.status, 'approved')
        
        # Perform search
        response = self.client.get(reverse('search:results'), {
            'q': 'wheat farming',
            'model': 'vsm',
            'lang': 'en'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify search history was created
        self.assertTrue(SearchHistory.objects.filter(
            user=self.user,
            query_text='wheat farming'
        ).exists())


class PerformanceTestCase(TestCase):
    """Performance and load tests."""
    
    def test_large_document_indexing(self):
        """Test indexing performance with larger documents."""
        # Create multiple documents
        for i in range(10):
            Document.objects.create(
                title=f"Document {i}",
                language='en',
                raw_text=" ".join([f"word{j}" for j in range(100)]),
                status='approved'
            )
        
        # Time the indexing
        import time
        start = time.time()
        
        indexer = Indexer()
        result = indexer.build_index(Document.objects.filter(status='approved'))
        
        duration = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds for 10 docs)
        self.assertLess(duration, 5.0)
        self.assertEqual(result['total_docs'], 10)
    
    def test_search_performance(self):
        """Test search performance."""
        # Create test data
        for i in range(20):
            doc = Document.objects.create(
                title=f"Doc {i}",
                language='en',
                raw_text=f"Content about topic {i % 5}",
                status='approved',
                is_indexed=True,
                word_count=10
            )
        
        # Build index
        indexer = Indexer()
        result = indexer.build_index(Document.objects.filter(status='approved'))
        
        for term, postings in result['index'].items():
            IndexEntry.objects.create(
                term=term,
                doc_frequency=len(postings),
                postings_json=json.dumps(postings)
            )
        
        # Time search
        import time
        start = time.time()
        
        vsm = VSM()
        results = vsm.search("topic content", language='en', top_k=10)
        
        duration = time.time() - start
        
        # Should be fast (< 1 second)
        self.assertLess(duration, 1.0)


# Run tests with: python manage.py test search
