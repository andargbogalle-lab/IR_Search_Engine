"""
Spell Checker for query correction.
Uses edit distance and frequency-based correction.
"""
import re
from collections import Counter
from search.models import IndexEntry, SpellCorrection


class SpellChecker:
    def __init__(self):
        self.word_freq = {}
        self.load_vocabulary()
    
    def load_vocabulary(self):
        """Load vocabulary from indexed terms."""
        try:
            terms = IndexEntry.objects.values_list('term', 'doc_frequency')
            self.word_freq = {term: freq for term, freq in terms}
        except Exception:
            self.word_freq = {}
    
    def edits1(self, word):
        """Generate all edits that are one edit away from word."""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)
    
    def edits2(self, word):
        """Generate all edits that are two edits away from word."""
        return set(e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))
    
    def known(self, words):
        """Return the subset of words that appear in the vocabulary."""
        return set(w for w in words if w in self.word_freq)
    
    def candidates(self, word):
        """Generate possible spelling corrections for word."""
        return (self.known([word]) or 
                self.known(self.edits1(word)) or 
                self.known(self.edits2(word)) or 
                [word])
    
    def correct(self, word):
        """Return the most probable spelling correction for word."""
        # Check database for known corrections first
        try:
            correction = SpellCorrection.objects.get(misspelled=word)
            return correction.corrected
        except SpellCorrection.DoesNotExist:
            pass
        
        # Find best candidate based on frequency
        candidates = self.candidates(word)
        best = max(candidates, key=lambda w: self.word_freq.get(w, 0))
        
        # Save correction if different
        if best != word and best in self.word_freq:
            SpellCorrection.objects.update_or_create(
                misspelled=word,
                defaults={'corrected': best, 'frequency': 1}
            )
        
        return best
    
    def correct_query(self, query_text):
        """Correct all words in a query."""
        words = re.findall(r'\b[a-z]+\b', query_text.lower())
        corrected_words = [self.correct(word) for word in words]
        
        # Return corrected query and whether any corrections were made
        corrected_query = ' '.join(corrected_words)
        has_corrections = corrected_query != ' '.join(words)
        
        return corrected_query, has_corrections
