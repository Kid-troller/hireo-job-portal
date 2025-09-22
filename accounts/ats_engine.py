import json
import re
from typing import Dict, List, Optional, Tuple
from collections import Counter

# Optional imports with fallbacks
NLTK_AVAILABLE = False
SKLEARN_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    pass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    pass

class ATSOptimizationEngine:
    """Advanced ATS optimization and analysis engine"""
    
    def __init__(self):
        self.strong_action_words = [
            'achieved', 'administered', 'analyzed', 'built', 'collaborated', 'created',
            'delivered', 'designed', 'developed', 'directed', 'enhanced', 'established',
            'executed', 'generated', 'implemented', 'improved', 'increased', 'initiated',
            'launched', 'led', 'managed', 'optimized', 'organized', 'produced',
            'reduced', 'resolved', 'streamlined', 'supervised', 'transformed'
        ]
        
        self.weak_words = [
            'responsible for', 'worked on', 'helped with', 'assisted', 'participated',
            'involved in', 'contributed to', 'supported', 'handled'
        ]
        
        self.ats_keywords = {
            'technology': ['python', 'java', 'javascript', 'react', 'angular', 'node.js', 'sql', 'aws', 'docker'],
            'marketing': ['seo', 'sem', 'social media', 'analytics', 'campaign', 'conversion', 'roi'],
            'finance': ['financial analysis', 'budgeting', 'forecasting', 'excel', 'modeling', 'compliance'],
            'healthcare': ['patient care', 'medical records', 'hipaa', 'clinical', 'treatment', 'diagnosis'],
            'sales': ['revenue', 'quota', 'pipeline', 'crm', 'negotiation', 'closing', 'prospecting']
        }
    
    def analyze_job_description(self, job_text: str) -> Dict:
        """Extract keywords and requirements from job description"""
        # Clean and tokenize text
        cleaned_text = self._clean_text(job_text)
        
        # Simple tokenization without NLTK
        tokens = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned_text.lower())
        
        # Basic stopwords list
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'among', 'this', 'that', 'these', 'those', 'will', 'would',
            'should', 'could', 'can', 'may', 'might', 'must', 'shall', 'have', 'has', 'had',
            'been', 'being', 'are', 'was', 'were', 'you', 'your', 'our', 'their'
        }
        
        # Filter tokens
        filtered_tokens = [w for w in tokens if w not in stop_words and len(w) > 2]
        
        # Extract key information
        skills = self._extract_skills(job_text)
        requirements = self._extract_requirements(job_text)
        experience_level = self._extract_experience_level(job_text)
        
        # Extract keywords based on frequency
        word_freq = Counter(filtered_tokens)
        keywords = [word for word, freq in word_freq.most_common(20) if len(word) > 3]
        
        return {
            'extracted_keywords': keywords,
            'required_skills': skills['required'],
            'preferred_skills': skills['preferred'],
            'experience_level': experience_level,
            'education_requirements': self._extract_education_requirements(job_text),
            'keyword_count': len(keywords),
            'analysis_score': self._calculate_analysis_quality(job_text)
        }
    
    def calculate_ats_score(self, resume_content: str, job_description: str = None) -> Dict:
        """Calculate comprehensive ATS score"""
        scores = {
            'overall_ats_score': 0,
            'keyword_match_score': 0,
            'formatting_score': 0,
            'content_relevance_score': 0
        }
        
        # Formatting score (40% of total)
        formatting_score = self._analyze_formatting(resume_content)
        scores['formatting_score'] = formatting_score
        
        # Content relevance score (30% of total)
        content_score = self._analyze_content_quality(resume_content)
        scores['content_relevance_score'] = content_score
        
        # Keyword match score (30% of total) - only if job description provided
        if job_description:
            keyword_score = self._calculate_keyword_match(resume_content, job_description)
            scores['keyword_match_score'] = keyword_score
        else:
            scores['keyword_match_score'] = 70  # Default score without job description
        
        # Calculate overall score
        scores['overall_ats_score'] = int(
            (scores['formatting_score'] * 0.4) +
            (scores['content_relevance_score'] * 0.3) +
            (scores['keyword_match_score'] * 0.3)
        )
        
        return scores
    
    def analyze_keyword_gaps(self, resume_content: str, job_keywords: List[str]) -> Dict:
        """Identify missing keywords and suggest improvements"""
        resume_words = set(word_tokenize(resume_content.lower()))
        job_words = set([kw.lower() for kw in job_keywords])
        
        matched = job_words.intersection(resume_words)
        missing = job_words - resume_words
        
        return {
            'matched_keywords': list(matched),
            'missing_keywords': list(missing),
            'match_percentage': len(matched) / len(job_words) * 100 if job_words else 0,
            'keyword_density': self._calculate_keyword_density(resume_content, job_keywords)
        }
    
    def enhance_bullet_points(self, bullet_points: List[str]) -> List[Dict]:
        """AI-enhance bullet points with strong action words and quantification"""
        enhanced_points = []
        
        for point in bullet_points:
            enhanced = self._enhance_single_bullet_point(point)
            enhanced_points.append(enhanced)
        
        return enhanced_points
    
    def _enhance_single_bullet_point(self, bullet_point: str) -> Dict:
        """Enhance a single bullet point"""
        original = bullet_point.strip()
        enhanced = original
        improvements = []
        
        # Replace weak words with strong action words
        for weak in self.weak_words:
            if weak in enhanced.lower():
                # Find appropriate replacement
                replacement = self._suggest_action_word(enhanced)
                if replacement:
                    enhanced = re.sub(re.escape(weak), replacement, enhanced, flags=re.IGNORECASE)
                    improvements.append(f"Replaced '{weak}' with '{replacement}'")
        
        # Add quantification suggestions
        if not re.search(r'\d+[%$]?|\d+\s*(percent|dollars|users|customers)', enhanced):
            improvements.append("Consider adding specific numbers or percentages")
        
        # Calculate scores
        original_score = self._score_bullet_point(original)
        enhanced_score = self._score_bullet_point(enhanced)
        
        return {
            'original_text': original,
            'enhanced_text': enhanced,
            'improvements_made': improvements,
            'original_score': original_score,
            'enhanced_score': enhanced_score,
            'improvement_percentage': ((enhanced_score - original_score) / original_score * 100) if original_score > 0 else 0
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        return text.strip()
    
    def _extract_skills(self, job_text: str) -> Dict:
        """Extract required and preferred skills from job description"""
        required_skills = []
        preferred_skills = []
        
        # Look for skill sections
        skill_patterns = [
            r'required skills?[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'must have[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'qualifications?[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                skills = [s.strip() for s in re.split(r'[,\n\-\•]', match) if s.strip()]
                required_skills.extend(skills[:5])  # Limit to top 5
        
        # Look for preferred skills
        preferred_patterns = [
            r'preferred[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'nice to have[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'bonus[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in preferred_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                skills = [s.strip() for s in re.split(r'[,\n\-\•]', match) if s.strip()]
                preferred_skills.extend(skills[:3])  # Limit to top 3
        
        return {
            'required': required_skills[:10],
            'preferred': preferred_skills[:5]
        }
    
    def _extract_requirements(self, job_text: str) -> List[str]:
        """Extract job requirements"""
        requirements = []
        
        # Look for requirement sections
        req_patterns = [
            r'requirements?[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'qualifications?[:\-]?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in req_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                reqs = [r.strip() for r in re.split(r'[,\n\-\•]', match) if r.strip()]
                requirements.extend(reqs[:5])
        
        return requirements[:10]
    
    def _extract_experience_level(self, job_text: str) -> str:
        """Extract required experience level"""
        experience_patterns = [
            (r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', 'years'),
            (r'entry\s*level', 'entry'),
            (r'junior', 'junior'),
            (r'senior', 'senior'),
            (r'lead', 'lead'),
            (r'principal', 'principal')
        ]
        
        for pattern, level in experience_patterns:
            if re.search(pattern, job_text, re.IGNORECASE):
                if level == 'years':
                    match = re.search(pattern, job_text, re.IGNORECASE)
                    return f"{match.group(1)} years"
                return level
        
        return 'not specified'
    
    def _extract_education_requirements(self, job_text: str) -> List[str]:
        """Extract education requirements"""
        education = []
        
        edu_patterns = [
            r"bachelor'?s?\s*(?:degree)?",
            r"master'?s?\s*(?:degree)?",
            r"phd|doctorate",
            r"high school|diploma",
            r"associate'?s?\s*(?:degree)?"
        ]
        
        for pattern in edu_patterns:
            if re.search(pattern, job_text, re.IGNORECASE):
                education.append(re.search(pattern, job_text, re.IGNORECASE).group())
        
        return education[:3]
    
    def _calculate_analysis_quality(self, job_text: str) -> float:
        """Calculate quality score of job description analysis"""
        score = 0.0
        
        # Length check
        if len(job_text) > 500:
            score += 25
        elif len(job_text) > 200:
            score += 15
        
        # Structure check
        if re.search(r'requirements?|qualifications?', job_text, re.IGNORECASE):
            score += 25
        
        if re.search(r'responsibilities?|duties', job_text, re.IGNORECASE):
            score += 25
        
        if re.search(r'skills?|experience', job_text, re.IGNORECASE):
            score += 25
        
        return min(score, 100.0)
    
    def _analyze_formatting(self, resume_content: str) -> int:
        """Analyze ATS-friendly formatting"""
        score = 100
        
        # Check for problematic elements
        if re.search(r'<table|<img|<canvas', resume_content, re.IGNORECASE):
            score -= 20
        
        # Check for proper headings
        if not re.search(r'(experience|education|skills)', resume_content, re.IGNORECASE):
            score -= 15
        
        # Check for consistent formatting
        if len(re.findall(r'\n\s*\n', resume_content)) < 3:
            score -= 10
        
        return max(score, 0)
    
    def _analyze_content_quality(self, resume_content: str) -> int:
        """Analyze content quality and relevance"""
        score = 0
        
        # Check for action words
        action_word_count = sum(1 for word in self.strong_action_words if word in resume_content.lower())
        score += min(action_word_count * 5, 30)
        
        # Check for quantification
        numbers = len(re.findall(r'\d+[%$]?|\d+\s*(percent|dollars|users|customers)', resume_content))
        score += min(numbers * 3, 25)
        
        # Check for professional sections
        sections = ['experience', 'education', 'skills', 'summary']
        section_count = sum(1 for section in sections if section in resume_content.lower())
        score += section_count * 10
        
        # Length check
        word_count = len(resume_content.split())
        if 300 <= word_count <= 800:
            score += 15
        elif word_count > 100:
            score += 10
        
        return min(score, 100)
    
    def _calculate_keyword_match(self, resume_content: str, job_description: str) -> int:
        """Calculate keyword match percentage"""
        # Extract keywords from job description
        job_analysis = self.analyze_job_description(job_description)
        job_keywords = job_analysis['extracted_keywords']
        
        if not job_keywords:
            return 70  # Default score
        
        # Count matches in resume
        resume_words = set(word_tokenize(resume_content.lower()))
        matches = sum(1 for keyword in job_keywords if keyword.lower() in resume_words)
        
        match_percentage = (matches / len(job_keywords)) * 100
        return min(int(match_percentage), 100)
    
    def _calculate_keyword_density(self, text: str, keywords: List[str]) -> Dict:
        """Calculate keyword density for each keyword"""
        words = word_tokenize(text.lower())
        total_words = len(words)
        
        density = {}
        for keyword in keywords:
            count = words.count(keyword.lower())
            density[keyword] = (count / total_words) * 100 if total_words > 0 else 0
        
        return density
    
    def _suggest_action_word(self, context: str) -> str:
        """Suggest appropriate action word based on context"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['manage', 'lead', 'supervise']):
            return 'led'
        elif any(word in context_lower for word in ['create', 'build', 'develop']):
            return 'developed'
        elif any(word in context_lower for word in ['improve', 'enhance', 'optimize']):
            return 'optimized'
        elif any(word in context_lower for word in ['analyze', 'research', 'study']):
            return 'analyzed'
        else:
            return 'achieved'
    
    def _score_bullet_point(self, bullet_point: str) -> int:
        """Score individual bullet point quality"""
        score = 0
        
        # Check for action words
        if any(word in bullet_point.lower() for word in self.strong_action_words):
            score += 30
        
        # Check for quantification
        if re.search(r'\d+[%$]?|\d+\s*(percent|dollars|users|customers)', bullet_point):
            score += 25
        
        # Check length (ideal 1-2 lines)
        if 50 <= len(bullet_point) <= 150:
            score += 20
        
        # Check for weak words (penalty)
        if any(weak in bullet_point.lower() for weak in self.weak_words):
            score -= 15
        
        # Check for specific achievements
        if any(word in bullet_point.lower() for word in ['increased', 'decreased', 'improved', 'reduced']):
            score += 15
        
        return max(min(score, 100), 0)
