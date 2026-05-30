"""
Query Expansion using pseudo-relevance feedback and synonyms.
"""
from collections import Counter
from search.models import IndexEntry
import math


class QueryExpander:
    def __init__(self):
        self.expansion_terms = 3  # Number of terms to add
    
    def expand_with_pseudo_relevance(self, original_query_terms, top_docs, doc_texts):
        """
        Expand query using Rocchio algorithm with pseudo-relevance feedback.
        
        Args:
            original_query_terms: List of original query terms
            top_docs: List of top K document IDs from initial search
            doc_texts: Dictionary mapping doc_id to document text
        
        Returns:
            List of expanded query terms
        """
        if not top_docs or not doc_texts:
            return original_query_terms
        
        # Extract terms from top documents
        term_scores = Counter()
        
        for doc_id in top_docs[:3]:  # Use top 3 documents
            if doc_id not in doc_texts:
                continue
            
            doc_text = doc_texts[doc_id].lower()
            words = doc_text.split()
            
            # Count term frequencies in relevant docs
            for word in words:
                if word not in original_query_terms and len(word) > 3:
                    term_scores[word] += 1
        
        # Get top expansion terms
        expansion_terms = [term for term, _ in term_scores.most_common(self.expansion_terms)]
        
        # Combine original and expansion terms
        expanded_query = original_query_terms + expansion_terms
        
        return expanded_query
    
    def expand_with_cooccurrence(self, query_terms):
        """
        Expand query based on term co-occurrence in the index.
        Find terms that frequently appear with query terms.
        """
        cooccurring_terms = Counter()
        
        for term in query_terms:
            try:
                entry = IndexEntry.objects.get(term=term)
                postings = entry.get_postings()
                
                # For each document containing this term
                for doc_id in postings.keys():
                    # Find other terms in the same document
                    # This is a simplified version - in production, you'd maintain
                    # a co-occurrence matrix
                    pass
                    
            except IndexEntry.DoesNotExist:
                continue
        
        return query_terms
    
    def expand_with_synonyms(self, query_terms):
        """
        Expand query with synonyms (placeholder for WordNet integration).
        """
        # This would integrate with NLTK WordNet for English
        # For now, return original terms
        expanded = query_terms.copy()
        
        # Example synonym mapping (in production, use WordNet)
        synonym_map = {
            'car': ['automobile', 'vehicle'],
            'happy': ['joyful', 'pleased'],
            'big': ['large', 'huge'],
        }
        
        for term in query_terms:
            if term in synonym_map:
                expanded.extend(synonym_map[term][:1])  # Add one synonym
        
        return expanded
