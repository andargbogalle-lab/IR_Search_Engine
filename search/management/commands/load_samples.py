import os
from django.core.management.base import BaseCommand
from django.conf import settings
from search.models import Document
import glob

class Command(BaseCommand):
    help = 'Loads sample text documents from the sample_docs directory'

    def handle(self, *args, **kwargs):
        sample_dir = getattr(settings, 'SAMPLE_DOCS_DIR', None)
        
        if not sample_dir or not os.path.exists(sample_dir):
            self.stdout.write(self.style.ERROR(f"Sample directory not found: {sample_dir}"))
            return
            
        self.stdout.write(f"Looking for .txt files in {sample_dir}...")
        txt_files = glob.glob(os.path.join(sample_dir, '*.txt'))
        
        if not txt_files:
            self.stdout.write(self.style.WARNING("No .txt files found in the sample directory."))
            return
            
        count = 0
        for file_path in txt_files:
            filename = os.path.basename(file_path)
            
            # Determine language based on filename prefix (am_ vs en_)
            language = 'am' if filename.startswith('am_') else 'en'
            
            # Title is filename without extension, replace underscores with spaces
            title = os.path.splitext(filename)[0].replace('_', ' ').title()
            if title.startswith('Am ') or title.startswith('En '):
                title = title[3:]
                
            # Make sure titles are unique per language
            unique_title = f"{title} [{language.upper()}]"
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Create or update document
                doc, created = Document.objects.get_or_create(
                    title=unique_title,
                    defaults={
                        'language': language,
                        'raw_text': content,
                        'file_path': file_path
                    }
                )
                
                if created:
                    count += 1
                    self.stdout.write(f"Loaded: {unique_title}")
                else:
                    self.stdout.write(f"Skipped existing: {unique_title}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error loading {filename}: {str(e)}"))
                
        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {count} new documents."))
