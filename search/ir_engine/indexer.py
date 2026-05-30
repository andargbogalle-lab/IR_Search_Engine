"""
Inverted Index Builder.
Creates the inverted index and precalculates TF-IDF weights (Pure Python implementation).
"""
from collections import defaultdict
import math
import json
from .preprocessor import Preprocessor

class Indexer:
    def __init__(self):
        self.preprocessor = Preprocessor()
    
    def build_index(self, documents):
        """
        Builds the inverted index from a list of Document model instances.
        Returns a dictionary representation of the index.
        """
        # index format: {term: {doc_id: {'tf': int, 'positions': [int, ...]}}}
        index = defaultdict(lambda: defaultdict(lambda: {'tf': 0, 'positions': []}))
        
        # document lengths for BM25
        doc_lengths = {}
        total_docs = len(documents)
        
        # First Pass: Calculate TF and document lengths
        for doc in documents:
            doc_id = str(doc.id)
            
            # Process text
            words = self.preprocessor.process_text(doc.raw_text, doc.language)
            doc_lengths[doc_id] = len(words)
            
            # Build basic positional index and term frequencies
            for pos, word in enumerate(words):
                index[word][doc_id]['tf'] += 1
                index[word][doc_id]['positions'].append(pos)
                
        # Second Pass: Calculate TF-IDF
        # We calculate doc vectors to L2 normalize them for cosine similarity
        doc_vector_norms = defaultdict(float)
        
        for term, postings in index.items():
            doc_frequency = len(postings)
            # IDF = log(N / df)
            idf = math.log(total_docs / doc_frequency) if doc_frequency > 0 else 0
            
            for doc_id, data in postings.items():
                tf = data['tf']
                # raw tf-idf weight
                weight = tf * idf
                data['tfidf_raw'] = weight
                
                # accumulate squared weights for L2 norm
                doc_vector_norms[doc_id] += weight ** 2
                
        # Third Pass: L2 Normalize TF-IDF weights
        for term, postings in index.items():
            for doc_id, data in postings.items():
                norm = math.sqrt(doc_vector_norms[doc_id]) if doc_vector_norms[doc_id] > 0 else 1.0
                data['tfidf'] = data['tfidf_raw'] / norm
                # Remove raw weight to save space
                del data['tfidf_raw']
        
        return {
            'index': index,
            'doc_lengths': doc_lengths,
            'total_docs': total_docs
        }
