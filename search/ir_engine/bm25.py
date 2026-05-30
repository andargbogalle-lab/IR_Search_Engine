"""
Okapi BM25 Ranking Model.
"""
import math
from .preprocessor import Preprocessor
from search.models import IndexEntry, Document

class BM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.preprocessor = Preprocessor()
        
    def search(self, query_text, language='en', top_k=10):
        """
        Search documents using Okapi BM25.
        """
        query_words = self.preprocessor.process_text(query_text, language)
        if not query_words:
            return []
            
        # Total documents
        N = Document.objects.filter(is_indexed=True).count()
        if N == 0:
            return []
            
        # Calculate Average Document Length (avgdl)
        total_length = sum(doc.word_count for doc in Document.objects.filter(is_indexed=True))
        avgdl = total_length / N if N > 0 else 1.0
        
        # Document scores
        scores = {}
        
        for term in set(query_words):
            try:
                entry = IndexEntry.objects.get(term=term)
                postings = entry.get_postings()
                n_q = entry.doc_frequency
                
                # IDF for BM25
                idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
                if idf < 0:
                    idf = 0.0  # Prevent negative IDF
                    
                for doc_id, data in postings.items():
                    doc_id_int = int(doc_id)
                    tf = data.get('tf', 0)
                    
                    # Get document length
                    try:
                        doc = Document.objects.get(id=doc_id_int)
                        doc_len = doc.word_count
                    except Document.DoesNotExist:
                        continue
                        
                    # BM25 Formula
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / avgdl))
                    score = idf * (numerator / denominator)
                    
                    scores[doc_id_int] = scores.get(doc_id_int, 0.0) + score
                    
            except IndexEntry.DoesNotExist:
                continue
                
        # Sort results
        results = [(doc_id, score) for doc_id, score in scores.items() if score > 0]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
