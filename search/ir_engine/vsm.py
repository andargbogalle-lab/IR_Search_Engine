"""
Vector Space Model (VSM) using TF-IDF and Cosine Similarity.
"""
import math
from .preprocessor import Preprocessor
from search.models import IndexEntry, Document

class VSM:
    def __init__(self):
        self.preprocessor = Preprocessor()
        
    def search(self, query_text, language='en', top_k=10):
        """
        Search documents using Vector Space Model (Cosine Similarity).
        """
        # Process query
        query_words = self.preprocessor.process_text(query_text, language)
        if not query_words:
            return []
            
        # Calculate query TF
        query_tf = {}
        for word in query_words:
            query_tf[word] = query_tf.get(word, 0) + 1
            
        # Fetch relevant postings from DB
        relevant_docs = {}  # doc_id -> score
        query_vector_norm = 0.0
        
        # Total docs for IDF calculation
        total_docs = Document.objects.filter(is_indexed=True).count()
        if total_docs == 0:
            return []
            
        for term, q_tf in query_tf.items():
            try:
                entry = IndexEntry.objects.get(term=term)
                postings = entry.get_postings()
                
                # IDF = log(N / df)
                idf = math.log(total_docs / entry.doc_frequency) if entry.doc_frequency > 0 else 0
                query_weight = q_tf * idf
                query_vector_norm += query_weight ** 2
                
                for doc_id, data in postings.items():
                    # TF-IDF precalculated during indexing
                    doc_weight = data.get('tfidf', 0.0)
                    
                    if doc_id not in relevant_docs:
                        relevant_docs[doc_id] = {'score': 0.0, 'doc_norm': 0.0}
                        
                    # Dot product accumulation
                    relevant_docs[doc_id]['score'] += query_weight * doc_weight
                    # We assume doc vectors are already length-normalized by sklearn
                    
            except IndexEntry.DoesNotExist:
                continue
                
        # Calculate final Cosine Similarity scores
        results = []
        query_norm = math.sqrt(query_vector_norm) if query_vector_norm > 0 else 1.0
        
        for doc_id, data in relevant_docs.items():
            # Scikit-learn TF-IDF vectors are already L2 normalized, 
            # so doc_norm is 1.0. Score = dot_product / query_norm
            final_score = data['score'] / query_norm
            
            if final_score > 0:
                results.append((int(doc_id), final_score))
                
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
