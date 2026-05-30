"""
Evaluator for measuring search engine performance (Precision@K, Recall).
"""
import json
from .vsm import VSM
from .bm25 import BM25
from search.models import EvaluationResult

class Evaluator:
    def __init__(self):
        self.vsm = VSM()
        self.bm25 = BM25()
        
    def evaluate(self, query_text, relevant_doc_ids, model_type='vsm', language='en', k=5):
        """
        Evaluate a query and calculate Precision@K and Recall.
        relevant_doc_ids: list of known relevant document IDs for this query
        """
        if model_type == 'vsm':
            results = self.vsm.search(query_text, language, top_k=k)
        else:
            results = self.bm25.search(query_text, language, top_k=k)
            
        retrieved_doc_ids = [doc_id for doc_id, _ in results]
        relevant_set = set(relevant_doc_ids)
        
        # Calculate relevant items retrieved in top K
        relevant_retrieved = [doc_id for doc_id in retrieved_doc_ids if doc_id in relevant_set]
        num_relevant_retrieved = len(relevant_retrieved)
        
        # Precision@K = (relevant docs in top K) / K
        # If retrieved is less than K, we still divide by min(K, len(retrieved)) or just K
        # Typically Precision@K strictly divides by K.
        precision_at_k = num_relevant_retrieved / k if k > 0 else 0.0
        
        # Recall = (relevant docs in top K) / (total relevant docs)
        total_relevant = len(relevant_set)
        recall = num_relevant_retrieved / total_relevant if total_relevant > 0 else 0.0
        
        # Save to DB
        eval_result = EvaluationResult.objects.create(
            query_text=query_text,
            model_used=model_type,
            precision_at_5=precision_at_k,
            recall=recall,
            results_json=json.dumps(retrieved_doc_ids),
            relevant_docs_json=json.dumps(relevant_doc_ids)
        )
        
        return {
            'precision_at_k': precision_at_k,
            'recall': recall,
            'retrieved': retrieved_doc_ids,
            'relevant_retrieved': relevant_retrieved,
            'evaluation_id': eval_result.id
        }
