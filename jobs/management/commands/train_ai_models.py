"""
Management command to train all AI/ML models for the job search system
Usage: python manage.py train_ai_models
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Train all AI/ML models for intelligent job search'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retraining even if models exist',
        )
        parser.add_argument(
            '--models',
            nargs='+',
            choices=['ml', 'semantic', 'candidate', 'all'],
            default=['all'],
            help='Specify which models to train',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting AI/ML Model Training for Hireo Job Portal')
        )
        
        start_time = timezone.now()
        models_to_train = options['models']
        force_retrain = options['force']
        verbose = options['verbose']
        
        if verbose:
            logging.basicConfig(level=logging.INFO)
        
        success_count = 0
        total_count = 0
        
        # Train ML recommendation models
        if 'ml' in models_to_train or 'all' in models_to_train:
            total_count += 1
            self.stdout.write('\nTraining ML Recommendation Models...')
            try:
                from jobs.ml_models import train_models
                success = train_models()
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS('[SUCCESS] ML recommendation models trained successfully')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('[ERROR] Failed to train ML recommendation models')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Error training ML models: {e}')
                )
        
        # Initialize semantic search
        if 'semantic' in models_to_train or 'all' in models_to_train:
            total_count += 1
            self.stdout.write('\nInitializing Semantic Search Engine...')
            try:
                from jobs.semantic_search import initialize_semantic_search
                success = initialize_semantic_search()
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS('[SUCCESS] Semantic search engine initialized successfully')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('[ERROR] Failed to initialize semantic search')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Error initializing semantic search: {e}')
                )
        
        # Train candidate ranking models
        if 'candidate' in models_to_train or 'all' in models_to_train:
            total_count += 1
            self.stdout.write('\nTraining Candidate Ranking Models...')
            try:
                from jobs.candidate_ranking import train_candidate_models
                success = train_candidate_models()
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS('[SUCCESS] Candidate ranking models trained successfully')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('[ERROR] Failed to train candidate ranking models')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Error training candidate models: {e}')
                )
        
        # Initialize complete AI/ML system
        if 'all' in models_to_train:
            total_count += 1
            self.stdout.write('\nInitializing Complete AI/ML System...')
            try:
                from jobs.ai_ml_integration import initialize_ai_ml_system
                success = initialize_ai_ml_system()
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS('[SUCCESS] Complete AI/ML system initialized successfully')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('[WARNING] AI/ML system partially initialized')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Error initializing AI/ML system: {e}')
                )
        
        # Summary
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Training Summary:')
        self.stdout.write(f'   - Models trained: {success_count}/{total_count}')
        self.stdout.write(f'   - Duration: {duration:.2f} seconds')
        self.stdout.write(f'   - Status: {"SUCCESS" if success_count == total_count else "PARTIAL"}')
        
        if success_count == total_count:
            self.stdout.write(
                self.style.SUCCESS('\nAll AI/ML models are ready for production!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\nSome models failed to train. Check logs for details.')
            )
        
        self.stdout.write('='*60)
        
        # Provide usage instructions
        self.stdout.write('\nNext Steps:')
        self.stdout.write('   1. Test the enhanced job search at /jobs/')
        self.stdout.write('   2. Try AI recommendations at /jobs/api/intelligent-recommendations/')
        self.stdout.write('   3. Use semantic search at /jobs/api/semantic-search/')
        self.stdout.write('   4. Check candidate recommendations for employers')
        self.stdout.write('\nYour job portal now has AI/ML superpowers!')
