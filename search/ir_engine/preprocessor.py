"""
Text Preprocessing module for English and Amharic.
Handles tokenization, stopword removal, and basic stemming/normalization.
"""
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import logging

logger = logging.getLogger(__name__)

# Ensure nltk resources are available
def download_nltk_data():
    """Download required NLTK data if not present."""
    required_data = ['stopwords', 'punkt']
    for data in required_data:
        try:
            nltk.data.find(f'corpora/{data}')
        except LookupError:
            try:
                nltk.download(data, quiet=True)
                logger.info(f"Downloaded NLTK data: {data}")
            except Exception as e:
                logger.error(f"Failed to download NLTK data {data}: {e}")

# Download on module import
download_nltk_data()


class Preprocessor:
    def __init__(self):
        try:
            self.english_stopwords = set(stopwords.words('english'))
        except Exception as e:
            logger.warning(f"Could not load English stopwords: {e}")
            self.english_stopwords = set()
        
        self.stemmer = PorterStemmer()
        
        # Enhanced Amharic stopwords
        self.amharic_stopwords = {
            "ነው", "እና", "ወይም", "ግን", "ስለዚህ", "ወደ", "ላይ", "ውስጥ", "ጋር", "እንደ", 
            "ነበር", "ናቸው", "አለ", "እስከ", "ይህ", "ያ", "ምን", "ማን", "እንዴት", "ለምን",
            "በ", "ከ", "ለ", "እንደ", "ስለ", "ምክንያት", "ምክንያቱም", "ነገር", "ግን"
        }

    def tokenize(self, text, language='en'):
        """Tokenize text into lowercase words."""
        if not text:
            return []
        
        # Lowercase for English, Amharic doesn't have casing but it's safe
        text = text.lower()
        
        if language == 'am':
            # Amharic Ethiopic script range and basic punctuation removal
            # Ethiopic Unicode block: \u1200-\u137F
            words = re.findall(r'[\u1200-\u137F]+', text)
        else:
            # English alphanumeric words (including numbers)
            words = re.findall(r'\b[a-z0-9]+\b', text)
            
        return words

    def remove_stopwords(self, words, language='en'):
        """Remove stopwords from a list of words."""
        if not words:
            return []
        
        if language == 'am':
            return [w for w in words if w not in self.amharic_stopwords]
        else:
            return [w for w in words if w not in self.english_stopwords]

    def stem(self, words, language='en'):
        """Apply stemming to a list of words."""
        if not words:
            return []
        
        if language == 'am':
            # Enhanced Amharic character normalization
            # Normalize different forms of the same character
            normalized = []
            for word in words:
                # Normalize ሀ, ሐ, ኀ to ሀ
                word = word.replace('ሐ', 'ሀ').replace('ኀ', 'ሀ')
                # Normalize ሰ, ሠ to ሰ
                word = word.replace('ሠ', 'ሰ')
                # Normalize ዐ, አ to አ
                word = word.replace('ዐ', 'አ')
                normalized.append(word)
            return normalized
        else:
            try:
                return [self.stemmer.stem(w) for w in words]
            except Exception as e:
                logger.error(f"Stemming error: {e}")
                return words

    def process_text(self, text, language='en'):
        """Complete preprocessing pipeline."""
        if not text:
            return []
        
        try:
            words = self.tokenize(text, language)
            words = self.remove_stopwords(words, language)
            words = self.stem(words, language)
            return words
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            return []
    
    def highlight_terms(self, text, query_terms, max_length=300):
        """
        Highlight query terms in text and return a snippet.
        Returns HTML with <mark> tags around matching terms.
        """
        if not text or not query_terms:
            return text[:max_length] + ('...' if len(text) > max_length else '')
        
        # Find first occurrence of any query term
        text_lower = text.lower()
        first_pos = len(text)
        
        for term in query_terms:
            pos = text_lower.find(term.lower())
            if pos != -1 and pos < first_pos:
                first_pos = pos
        
        # Extract snippet around first occurrence
        start = max(0, first_pos - 100)
        end = min(len(text), first_pos + max_length - 100)
        snippet = text[start:end]
        
        if start > 0:
            snippet = '...' + snippet
        if end < len(text):
            snippet = snippet + '...'
        
        # Highlight terms (case-insensitive)
        for term in query_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            snippet = pattern.sub(lambda m: f'<mark>{m.group()}</mark>', snippet)
        
        return snippet

