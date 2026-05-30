from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q, F, Avg
from django.db import models
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .models import Document, EvaluationResult, IndexEntry, SearchHistory, QuerySuggestion
from .ir_engine import VSM, BM25, Evaluator, Indexer
from .ir_engine.spell_checker import SpellChecker
from .ir_engine.query_expander import QueryExpander
import time
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


class HomeView(View):
    def get(self, request):
        doc_count = Document.objects.filter(is_indexed=True, status='approved').count()
        
        # Get popular queries for suggestions
        popular_queries = QuerySuggestion.objects.all()[:10]
        
        # Get recent searches for logged-in users
        recent_searches = []
        if request.user.is_authenticated:
            recent_searches = SearchHistory.objects.filter(user=request.user)[:5]
        
        context = {
            'doc_count': doc_count,
            'popular_queries': popular_queries,
            'recent_searches': recent_searches,
        }
        return render(request, 'search/home.html', context)

@method_decorator(ratelimit(key='ip', rate='30/m', method='GET'), name='dispatch')
class ResultsView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        model_type = request.GET.get('model', 'vsm')
        language = request.GET.get('lang', 'en')
        page_number = request.GET.get('page', 1)
        use_expansion = request.GET.get('expand', 'false') == 'true'
        
        # Validate query length
        max_length = getattr(settings, 'MAX_QUERY_LENGTH', 500)
        if len(query) > max_length:
            query = query[:max_length]
        
        if not query:
            return render(request, 'search/results.html', {'query': ''})
        
        # Update query suggestions
        try:
            suggestion = QuerySuggestion.objects.get(query_text=query)
            suggestion.search_count += 1
            suggestion.save()
        except QuerySuggestion.DoesNotExist:
            QuerySuggestion.objects.create(query_text=query, search_count=1)
        
        # Spell checking
        spell_checker = SpellChecker()
        corrected_query, has_correction = spell_checker.correct_query(query)
        
        # Use corrected query if different
        search_query = corrected_query if has_correction else query
        
        # Determine model name
        if model_type == 'bm25':
            model_name = "Okapi BM25"
        else:
            model_name = "Vector Space Model (TF-IDF)"
        
        # Generate cache key
        cache_key = f"search:{model_type}:{language}:{hashlib.md5(search_query.encode()).hexdigest()}"
        
        # Try to get from cache
        cached_results = cache.get(cache_key)
        
        if cached_results:
            raw_results = cached_results['results']
            execution_time = cached_results['time']
            from_cache = True
            logger.info(f"Cache hit for query: {search_query}")
        else:
            start_time = time.time()
            
            # Select Model
            if model_type == 'bm25':
                engine = BM25()
            else:
                engine = VSM()
            
            # Execute Search
            raw_results = engine.search(search_query, language=language, top_k=50)
            
            # Query expansion if requested and results are few
            if use_expansion and len(raw_results) < 5:
                expander = QueryExpander()
                from .ir_engine.preprocessor import Preprocessor
                preprocessor = Preprocessor()
                query_terms = preprocessor.process_text(search_query, language)
                
                # Get top doc texts for expansion
                top_doc_ids = [doc_id for doc_id, _ in raw_results[:3]]
                doc_texts = {}
                for doc_id in top_doc_ids:
                    try:
                        doc = Document.objects.get(id=doc_id)
                        doc_texts[doc_id] = doc.raw_text
                    except Document.DoesNotExist:
                        pass
                
                expanded_terms = expander.expand_with_pseudo_relevance(
                    query_terms, top_doc_ids, doc_texts
                )
                
                if len(expanded_terms) > len(query_terms):
                    expanded_query = ' '.join(expanded_terms)
                    raw_results = engine.search(expanded_query, language=language, top_k=50)
            
            execution_time = round(time.time() - start_time, 4)
            from_cache = False
            
            # Cache results for 5 minutes
            cache.set(cache_key, {
                'results': raw_results,
                'time': execution_time
            }, 300)
        
        # Fetch documents for results with pagination
        results = []
        for doc_id, score in raw_results:
            try:
                doc = Document.objects.get(id=doc_id, status='approved')
                
                # Increment search count
                doc.increment_search_count()
                
                # Get highlighted snippet
                from .ir_engine.preprocessor import Preprocessor
                preprocessor = Preprocessor()
                query_terms = preprocessor.process_text(search_query, language)
                highlighted_snippet = preprocessor.highlight_terms(
                    doc.raw_text, query_terms, max_length=300
                )
                
                results.append({
                    'document': doc,
                    'score': score,
                    'snippet': highlighted_snippet
                })
            except Document.DoesNotExist:
                continue
        
        # Pagination
        results_per_page = getattr(settings, 'RESULTS_PER_PAGE', 10)
        paginator = Paginator(results, results_per_page)
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Save search history
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                user=request.user,
                query_text=query,
                model_used=model_type,
                language=language,
                results_count=len(results),
                execution_time=execution_time
            )
        
        context = {
            'query': query,
            'corrected_query': corrected_query if has_correction else None,
            'page_obj': page_obj,
            'model_name': model_name if not from_cache else f"{model_name} (Cached)",
            'model_type': model_type,
            'language': language,
            'execution_time': execution_time,
            'result_count': len(results),
            'from_cache': from_cache,
            'use_expansion': use_expansion,
        }
        
        return render(request, 'search/results.html', context)

class EvaluateView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        evals = EvaluationResult.objects.all()[:10]
        return render(request, 'search/evaluate.html', {'evals': evals})
        
    def post(self, request):
        query = request.POST.get('query')
        relevant_ids_str = request.POST.get('relevant_ids', '')
        model_type = request.POST.get('model', 'vsm')
        language = request.POST.get('lang', 'en')
        
        try:
            # Parse comma-separated IDs
            relevant_ids = [int(i.strip()) for i in relevant_ids_str.split(',') if i.strip().isdigit()]
            
            if query and relevant_ids:
                evaluator = Evaluator()
                result = evaluator.evaluate(query, relevant_ids, model_type, language, k=5)
                success_msg = f"Evaluation saved. Precision@5: {result['precision_at_k']:.2f}, Recall: {result['recall']:.2f}"
            else:
                success_msg = "Invalid input. Please provide a query and at least one relevant document ID."
                
        except Exception as e:
            success_msg = f"Error during evaluation: {str(e)}"
            
        evals = EvaluationResult.objects.all()[:10]
        return render(request, 'search/evaluate.html', {
            'evals': evals,
            'message': success_msg
        })

@method_decorator(ratelimit(key='user', rate='10/h', method='POST'), name='post')
class UploadView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'search/upload.html')
        
    def post(self, request):
        title = request.POST.get('title', '').strip()
        language = request.POST.get('language', 'en')
        uploaded_file = request.FILES.get('document_file')
        
        if not title or not uploaded_file:
            return render(request, 'search/upload.html', {
                'error': 'Please provide a title and a file.'
            })
        
        # Validate file size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10485760)  # 10MB
        if uploaded_file.size > max_size:
            return render(request, 'search/upload.html', {
                'error': f'File too large. Maximum size is {max_size // 1048576}MB.'
            })
        
        # Validate file extension
        allowed_extensions = ['.txt', '.pdf']  # Only txt and pdf supported
        file_ext = '.' + uploaded_file.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            return render(request, 'search/upload.html', {
                'error': f'Invalid file type. Only .txt and .pdf files are supported.'
            })
        
        try:
            # Read text from file based on extension
            if file_ext == '.pdf':
                # Extract text from PDF using PyPDF2
                try:
                    from PyPDF2 import PdfReader
                    import io
                    pdf_file = io.BytesIO(uploaded_file.read())
                    pdf_reader = PdfReader(pdf_file)
                    content = ''
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            content += page_text + '\n'
                    
                    if not content.strip():
                        return render(request, 'search/upload.html', {
                            'error': 'PDF file contains no extractable text. It may be an image-based PDF. Please use a text-based PDF or convert to .txt format.'
                        })
                        
                except Exception as pdf_error:
                    logger.error(f"PDF extraction error: {pdf_error}")
                    return render(request, 'search/upload.html', {
                        'error': f'Error reading PDF file: {str(pdf_error)}'
                    })
            
            else:  # .txt file
                content = uploaded_file.read().decode('utf-8', errors='ignore')
            
            # Sanitize content
            import bleach
            content = bleach.clean(content, tags=[], strip=True)
            
            if not content.strip():
                return render(request, 'search/upload.html', {
                    'error': 'File appears to be empty or unreadable.'
                })
            
            # Calculate checksum for duplicate detection
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            # Check for duplicates
            if Document.objects.filter(checksum=checksum).exists():
                return render(request, 'search/upload.html', {
                    'error': 'This document already exists in the system.'
                })
            
            # Save document
            status = 'approved' if request.user.is_staff else 'pending'
            doc = Document.objects.create(
                title=title,
                language=language,
                raw_text=content,
                is_indexed=False,
                owner=request.user,
                status=status,
                file_size=uploaded_file.size,
                checksum=checksum
            )
            
            if status == 'approved':
                # Trigger re-indexing (in production, use Celery task)
                try:
                    self._reindex_documents()
                    success_msg = f"Document '{title}' uploaded and indexed successfully!"
                except Exception as e:
                    logger.error(f"Indexing error: {e}")
                    success_msg = f"Document '{title}' uploaded but indexing failed. Contact admin."
            else:
                success_msg = f"Document '{title}' uploaded successfully and is pending admin approval."
            
            return render(request, 'search/upload.html', {'message': success_msg})
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return render(request, 'search/upload.html', {
                'error': f"Error processing file: {str(e)}"
            })
    
    def _reindex_documents(self):
        """Helper method to reindex all approved documents."""
        all_docs = Document.objects.filter(status='approved')
        indexer = Indexer()
        result = indexer.build_index(all_docs)
        
        index_data = result['index']
        doc_lengths = result['doc_lengths']
        
        # Update word counts
        for doc_id_str, length in doc_lengths.items():
            Document.objects.filter(id=int(doc_id_str)).update(
                word_count=length,
                is_indexed=True,
                last_indexed=timezone.now()
            )
        
        # Update inverted index in DB
        IndexEntry.objects.all().delete()
        entries_to_create = [
            IndexEntry(
                term=term,
                doc_frequency=len(postings),
                postings_json=json.dumps(postings)
            )
            for term, postings in index_data.items()
        ]
        
        # Batch save
        batch_size = 1000
        for i in range(0, len(entries_to_create), batch_size):
            IndexEntry.objects.bulk_create(entries_to_create[i:i+batch_size])
        
        # Clear search cache after reindexing
        cache.clear()
        logger.info(f"Reindexed {len(all_docs)} documents")

class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'registration/register.html', {'form': form})
        
    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('search:home')
        return render(request, 'registration/register.html', {'form': form})

class DocumentDetailView(View):
    def get(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id)
        action = request.GET.get('action')
        
        # Determine if user is permitted (public if approved, or owner/admin if pending)
        is_permitted = (
            doc.status == 'approved' or 
            request.user.is_staff or 
            doc.owner == request.user
        )
        
        if not is_permitted:
            return render(request, 'search/results.html', {
                'error': 'You do not have permission to view this document.'
            })
        
        # Increment view count
        doc.increment_view_count()
        
        if action == 'download':
            from django.http import HttpResponse
            response = HttpResponse(doc.raw_text, content_type='text/plain; charset=utf-8')
            safe_title = "".join(c for c in doc.title if c.isalnum() or c in (' ', '-', '_'))
            response['Content-Disposition'] = f'attachment; filename="{safe_title}.txt"'
            return response
        
        # Get related documents (same language, similar topics)
        related_docs = Document.objects.filter(
            language=doc.language,
            status='approved',
            is_indexed=True
        ).exclude(id=doc.id)[:5]
        
        context = {
            'document': doc,
            'related_docs': related_docs,
        }
        return render(request, 'search/document_detail.html', context)


class SearchHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        history = SearchHistory.objects.filter(user=request.user)
        
        # Pagination
        paginator = Paginator(history, 20)
        page_number = request.GET.get('page', 1)
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Get statistics
        total_searches = history.count()
        avg_results = history.aggregate(models.Avg('results_count'))['results_count__avg'] or 0
        avg_time = history.aggregate(models.Avg('execution_time'))['execution_time__avg'] or 0
        
        context = {
            'page_obj': page_obj,
            'total_searches': total_searches,
            'avg_results': round(avg_results, 1),
            'avg_time': round(avg_time, 4),
        }
        return render(request, 'search/history.html', context)


class AutocompleteView(View):
    """AJAX endpoint for query autocomplete."""
    def get(self, request):
        from django.http import JsonResponse
        
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse({'suggestions': []})
        
        # Get suggestions from popular queries
        suggestions = QuerySuggestion.objects.filter(
            query_text__istartswith=query
        ).values_list('query_text', flat=True)[:10]
        
        return JsonResponse({'suggestions': list(suggestions)})

