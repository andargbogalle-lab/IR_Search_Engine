"""
IR Engine package for Information Retrieval algorithms.
"""
from .preprocessor import Preprocessor
from .indexer import Indexer
from .vsm import VSM
from .bm25 import BM25
from .evaluator import Evaluator
from .spell_checker import SpellChecker
from .query_expander import QueryExpander

__all__ = [
    'Preprocessor',
    'Indexer',
    'VSM',
    'BM25',
    'Evaluator',
    'SpellChecker',
    'QueryExpander',
]

__version__ = '2.0.0'
