# IR Search Engine

Information Retrieval Search Engine with bilingual support (English & Amharic)

## Features
- Vector Space Model (TF-IDF)
- BM25 Ranking
- Tokenization, Stopword Removal, Stemming
- Query Expansion & Spell Checking
- Document Upload (.txt, .pdf)
- Search History & Analytics

## Team Members
1. ANDARGACHEW BOGALE - 0248/16
2. MAREY GASHAW - 1226/16
3. WONDATIR FETENE - 2003/16
4. MEAZA WONDYE - 1252/16
5. HUSEN ALI - 1071/16
6. HAYMANOT FENTAW - 1021/16

## Quick Start

### Local Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m nltk.downloader punkt stopwords
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Admin Access
- Username: admin
- Password: admin123

## Deployment
See DEPLOYMENT_GUIDE.md for detailed instructions.
