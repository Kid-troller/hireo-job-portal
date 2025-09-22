"""
Semantic Search and NLP Processing for Job Search
Implements BERT-based semantic search, query expansion, and resume parsing
"""

import re
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging

# NLP Libraries with graceful fallbacks
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("sentence-transformers not available, using TF-IDF fallback")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("spaCy not available, using basic NLP processing")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from django.db.models import Q
from django.core.cache import cache
from django.conf import settings

from .models import JobPost, JobCategory
from accounts.models import JobSeekerProfile

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

class SemanticSearchEngine:
    """Advanced semantic search using sentence transformers"""
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self.job_embeddings = None
        self.job_ids = []
        self.job_texts = []
        self.is_initialized = False
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.is_initialized = True
                logger.info(f"Semantic search model loaded: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load sentence transformer: {e}")
                self.is_initialized = False
        else:
            logger.warning("sentence-transformers not available, using fallback TF-IDF")
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2)
            )
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.lower()
    
    def extract_job_text(self, job: JobPost) -> str:
        """Extract searchable text from job posting"""
        text_parts = []
        
        if job.title:
            text_parts.append(f"Title: {job.title}")
        
        if job.description:
            text_parts.append(f"Description: {job.description}")
        
        if job.requirements:
            text_parts.append(f"Requirements: {job.requirements}")
        
        if job.required_skills:
            text_parts.append(f"Skills: {job.required_skills}")
        
        if job.responsibilities:
            text_parts.append(f"Responsibilities: {job.responsibilities}")
        
        if job.category:
            text_parts.append(f"Category: {job.category.name}")
        
        if job.location:
            text_parts.append(f"Location: {job.location.city} {job.location.state}")
        
        if job.company:
            text_parts.append(f"Company: {job.company.name}")
        
        return self.preprocess_text(' '.join(text_parts))
    
    def build_job_index(self):
        """Build semantic index for all active jobs"""
        try:
            jobs = JobPost.objects.filter(status='active').select_related(
                'category', 'location', 'company'
            )
            
            self.job_texts = []
            self.job_ids = []
            
            for job in jobs:
                job_text = self.extract_job_text(job)
                self.job_texts.append(job_text)
                self.job_ids.append(job.id)
            
            if not self.job_texts:
                logger.warning("No jobs found for semantic indexing")
                return False
            
            if self.is_initialized and self.model:
                # Use sentence transformers for embeddings
                self.job_embeddings = self.model.encode(
                    self.job_texts,
                    convert_to_tensor=False,
                    show_progress_bar=True
                )
                logger.info(f"Built semantic index for {len(self.job_texts)} jobs using BERT")
            else:
                # Fallback to TF-IDF
                self.job_embeddings = self.tfidf_vectorizer.fit_transform(self.job_texts)
                logger.info(f"Built TF-IDF index for {len(self.job_texts)} jobs")
            
            return True
            
        except Exception as e:
            logger.error(f"Error building job index: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 20) -> List[Dict]:
        """Perform semantic search on job postings"""
        if not self.job_embeddings or not query.strip():
            return []
        
        try:
            processed_query = self.preprocess_text(query)
            
            if self.is_initialized and self.model:
                # Use sentence transformers
                query_embedding = self.model.encode([processed_query])
                similarities = cosine_similarity(query_embedding, self.job_embeddings)[0]
            else:
                # Use TF-IDF
                query_vector = self.tfidf_vectorizer.transform([processed_query])
                similarities = cosine_similarity(query_vector, self.job_embeddings)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for i, idx in enumerate(top_indices):
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    results.append({
                        'job_id': self.job_ids[idx],
                        'similarity_score': float(similarities[idx]),
                        'rank': i + 1
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

class QueryExpansionEngine:
    """Query expansion using synonyms and related terms"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Job-specific synonym mappings
        self.job_synonyms = {
            'developer': ['programmer', 'engineer', 'coder', 'software engineer'],
            'manager': ['supervisor', 'lead', 'director', 'head'],
            'analyst': ['researcher', 'specialist', 'consultant'],
            'designer': ['artist', 'creative', 'ui designer', 'ux designer'],
            'sales': ['business development', 'account manager', 'sales representative'],
            'marketing': ['digital marketing', 'content marketing', 'brand manager'],
            'data': ['data science', 'analytics', 'big data', 'machine learning'],
            'frontend': ['front-end', 'ui', 'user interface', 'client-side'],
            'backend': ['back-end', 'server-side', 'api', 'database'],
            'fullstack': ['full-stack', 'full stack', 'end-to-end'],
            'remote': ['work from home', 'telecommute', 'distributed'],
            'junior': ['entry level', 'associate', 'trainee'],
            'senior': ['experienced', 'lead', 'principal', 'expert'],
        }
        
        # Skill synonyms
        self.skill_synonyms = {
            'python': ['django', 'flask', 'fastapi'],
            'javascript': ['js', 'node.js', 'react', 'vue', 'angular'],
            'java': ['spring', 'hibernate', 'maven'],
            'sql': ['mysql', 'postgresql', 'database', 'rdbms'],
            'aws': ['amazon web services', 'cloud', 'ec2', 's3'],
            'docker': ['containerization', 'kubernetes', 'devops'],
            'machine learning': ['ml', 'ai', 'artificial intelligence', 'deep learning'],
        }
    
    def get_wordnet_synonyms(self, word: str) -> List[str]:
        """Get synonyms from WordNet"""
        synonyms = set()
        
        try:
            for syn in wordnet.synsets(word):
                for lemma in syn.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if synonym != word and len(synonym) > 2:
                        synonyms.add(synonym)
        except Exception:
            pass
        
        return list(synonyms)[:3]  # Limit to top 3
    
    def expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms"""
        try:
            original_query = query.lower().strip()
            expanded_terms = [original_query]
            
            # Tokenize query
            tokens = word_tokenize(original_query)
            tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
            
            for token in tokens:
                # Check job synonyms
                if token in self.job_synonyms:
                    expanded_terms.extend(self.job_synonyms[token][:2])
                
                # Check skill synonyms
                if token in self.skill_synonyms:
                    expanded_terms.extend(self.skill_synonyms[token][:2])
                
                # Get WordNet synonyms
                wordnet_synonyms = self.get_wordnet_synonyms(token)
                expanded_terms.extend(wordnet_synonyms)
            
            # Remove duplicates and join
            unique_terms = list(dict.fromkeys(expanded_terms))
            return ' '.join(unique_terms[:10])  # Limit expansion
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return query

class ResumeParser:
    """NLP-based resume parsing and analysis"""
    
    def __init__(self):
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
        
        # Skill patterns
        self.skill_patterns = {
            'programming': r'\b(python|java|javascript|c\+\+|c#|php|ruby|go|rust|swift|kotlin)\b',
            'web': r'\b(html|css|react|angular|vue|node\.js|django|flask|spring|laravel)\b',
            'database': r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|oracle)\b',
            'cloud': r'\b(aws|azure|gcp|docker|kubernetes|terraform|jenkins)\b',
            'data': r'\b(pandas|numpy|tensorflow|pytorch|scikit-learn|tableau|power bi)\b',
        }
    
    def extract_text_from_resume(self, resume_file) -> str:
        """Extract text from resume file"""
        try:
            # This is a simplified version - in production, you'd use libraries like
            # PyPDF2, python-docx, or pdfplumber for different file formats
            if hasattr(resume_file, 'read'):
                content = resume_file.read()
                if isinstance(content, bytes):
                    return content.decode('utf-8', errors='ignore')
                return str(content)
            return ""
        except Exception as e:
            logger.error(f"Error extracting text from resume: {e}")
            return ""
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text"""
        skills = []
        text_lower = text.lower()
        
        for category, pattern in self.skill_patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.extend(matches)
        
        # Remove duplicates and return
        return list(set(skills))
    
    def extract_experience_years(self, text: str) -> int:
        """Extract years of experience from resume"""
        try:
            # Look for patterns like "5 years experience", "3+ years", etc.
            patterns = [
                r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
                r'(\d+)\+?\s*yrs?\s*(?:of\s*)?(?:experience|exp)',
                r'experience\s*:?\s*(\d+)\+?\s*years?',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text.lower())
                if matches:
                    return int(matches[0])
            
            return 0
        except Exception:
            return 0
    
    def extract_education(self, text: str) -> List[str]:
        """Extract education information"""
        education = []
        
        # Common degree patterns
        degree_patterns = [
            r'\b(bachelor|master|phd|doctorate|mba|b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?a\.?)\b',
            r'\b(computer science|engineering|business|marketing|finance)\b',
        ]
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            education.extend(matches)
        
        return list(set(education))
    
    def parse_resume(self, resume_text: str) -> Dict:
        """Parse resume and extract structured information"""
        try:
            parsed_data = {
                'skills': self.extract_skills(resume_text),
                'experience_years': self.extract_experience_years(resume_text),
                'education': self.extract_education(resume_text),
                'text_length': len(resume_text),
            }
            
            # Use spaCy for additional NLP if available
            if self.nlp:
                doc = self.nlp(resume_text[:1000])  # Limit for performance
                
                # Extract entities
                entities = []
                for ent in doc.ents:
                    if ent.label_ in ['ORG', 'PERSON', 'GPE']:
                        entities.append({
                            'text': ent.text,
                            'label': ent.label_
                        })
                
                parsed_data['entities'] = entities
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return {}

class SmartFilterSuggester:
    """Intelligent filter suggestions based on query and user behavior"""
    
    def __init__(self):
        self.query_expander = QueryExpansionEngine()
    
    def suggest_filters_for_query(self, query: str) -> Dict:
        """Suggest relevant filters based on search query"""
        suggestions = {}
        query_lower = query.lower()
        
        # Experience level suggestions
        if any(term in query_lower for term in ['junior', 'entry', 'trainee', 'graduate']):
            suggestions['experience_level'] = 'entry'
        elif any(term in query_lower for term in ['senior', 'lead', 'principal', 'expert']):
            suggestions['experience_level'] = 'senior'
        elif any(term in query_lower for term in ['mid', 'intermediate']):
            suggestions['experience_level'] = 'mid'
        
        # Employment type suggestions
        if any(term in query_lower for term in ['intern', 'internship']):
            suggestions['employment_type'] = 'internship'
        elif any(term in query_lower for term in ['contract', 'freelance', 'consultant']):
            suggestions['employment_type'] = 'contract'
        elif any(term in query_lower for term in ['part time', 'part-time']):
            suggestions['employment_type'] = 'part_time'
        
        # Remote work suggestions
        if any(term in query_lower for term in ['remote', 'work from home', 'telecommute']):
            suggestions['is_remote'] = True
        
        # Category suggestions based on keywords
        category_keywords = {
            'software': ['developer', 'programmer', 'engineer', 'coding'],
            'marketing': ['marketing', 'seo', 'content', 'social media'],
            'sales': ['sales', 'business development', 'account manager'],
            'design': ['designer', 'ui', 'ux', 'graphic', 'creative'],
            'data': ['data', 'analyst', 'scientist', 'analytics'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                try:
                    job_category = JobCategory.objects.filter(
                        name__icontains=category
                    ).first()
                    if job_category:
                        suggestions['category'] = job_category.id
                        break
                except Exception:
                    pass
        
        return suggestions
    
    def get_popular_filters_for_category(self, category_id: int) -> Dict:
        """Get popular filters for a specific job category"""
        try:
            # This would analyze historical data to find popular filters
            # For now, return some defaults based on category
            category = JobCategory.objects.get(id=category_id)
            category_name = category.name.lower()
            
            suggestions = {}
            
            if 'software' in category_name or 'tech' in category_name:
                suggestions.update({
                    'is_remote': True,
                    'employment_type': 'full_time',
                })
            elif 'marketing' in category_name:
                suggestions.update({
                    'employment_type': 'full_time',
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting popular filters: {e}")
            return {}

# Global instances
semantic_engine = SemanticSearchEngine()
query_expander = QueryExpansionEngine()
resume_parser = ResumeParser()
filter_suggester = SmartFilterSuggester()

def initialize_semantic_search():
    """Initialize semantic search engine"""
    try:
        success = semantic_engine.build_job_index()
        if success:
            logger.info("Semantic search engine initialized successfully")
        return success
    except Exception as e:
        logger.error(f"Error initializing semantic search: {e}")
        return False

def perform_semantic_search(query: str, top_k: int = 20) -> List[int]:
    """Perform semantic search and return job IDs"""
    try:
        # Expand query for better matching
        expanded_query = query_expander.expand_query(query)
        
        # Perform semantic search
        results = semantic_engine.semantic_search(expanded_query, top_k)
        
        # Return job IDs in order of relevance
        return [result['job_id'] for result in results]
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return []

def get_smart_filter_suggestions(query: str, category_id: Optional[int] = None) -> Dict:
    """Get intelligent filter suggestions"""
    try:
        suggestions = filter_suggester.suggest_filters_for_query(query)
        
        if category_id:
            category_suggestions = filter_suggester.get_popular_filters_for_category(category_id)
            suggestions.update(category_suggestions)
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting filter suggestions: {e}")
        return {}
