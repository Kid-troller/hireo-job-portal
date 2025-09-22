import re
import json
from typing import Dict, List, Any
from datetime import datetime
import random

class ResumeAI:
    """AI-powered resume enhancement and optimization"""
    
    def __init__(self):
        self.action_word_categories = {
            'leadership': ['led', 'directed', 'managed', 'supervised', 'coordinated', 'guided', 'mentored'],
            'achievement': ['achieved', 'accomplished', 'delivered', 'exceeded', 'surpassed', 'attained'],
            'creation': ['created', 'developed', 'designed', 'built', 'established', 'launched', 'initiated'],
            'improvement': ['improved', 'enhanced', 'optimized', 'streamlined', 'upgraded', 'refined'],
            'analysis': ['analyzed', 'evaluated', 'assessed', 'researched', 'investigated', 'examined'],
            'collaboration': ['collaborated', 'partnered', 'coordinated', 'facilitated', 'negotiated'],
            'technical': ['implemented', 'configured', 'programmed', 'automated', 'integrated', 'deployed']
        }
        
        self.quantification_suggestions = [
            "Consider adding specific numbers (e.g., '20% increase', '500+ users')",
            "Include metrics like percentages, dollar amounts, or timeframes",
            "Add scale indicators (team size, budget, duration)",
            "Specify measurable outcomes or results"
        ]
        
        self.industry_keywords = {
            'technology': ['agile', 'scrum', 'api', 'cloud', 'devops', 'ci/cd', 'microservices', 'scalability'],
            'marketing': ['roi', 'conversion', 'engagement', 'analytics', 'segmentation', 'attribution'],
            'finance': ['roi', 'budget', 'forecast', 'compliance', 'risk management', 'financial modeling'],
            'healthcare': ['patient care', 'compliance', 'hipaa', 'quality assurance', 'clinical protocols'],
            'sales': ['pipeline', 'quota', 'conversion', 'crm', 'lead generation', 'customer acquisition']
        }
    
    def generate_professional_summary(self, user_data: Dict) -> Dict:
        """Generate AI-powered professional summary"""
        experience_years = user_data.get('experience_years', 0)
        skills = user_data.get('skills', [])
        industry = user_data.get('industry', 'general')
        
        # Create summary based on experience level
        if experience_years < 2:
            template = "Motivated {role} with {years} of experience in {industry}. Skilled in {top_skills} with a passion for {focus_area}. Seeking to leverage {strength} to contribute to {goal}."
        elif experience_years < 5:
            template = "Results-driven {role} with {years} years of experience in {industry}. Proven track record in {achievements}. Expert in {top_skills} with demonstrated ability to {capability}."
        else:
            template = "Senior {role} with {years}+ years of progressive experience in {industry}. Recognized leader in {specialization} with expertise in {top_skills}. Track record of {major_achievements}."
        
        # Fill template with user data
        summary_data = {
            'role': user_data.get('target_role', 'professional'),
            'years': experience_years,
            'industry': industry,
            'top_skills': ', '.join(skills[:3]) if skills else 'various technologies',
            'focus_area': self._get_focus_area(industry),
            'strength': self._get_strength_area(skills),
            'goal': self._get_career_goal(industry),
            'achievements': self._get_achievement_area(industry),
            'capability': self._get_capability_phrase(industry),
            'specialization': self._get_specialization(industry),
            'major_achievements': self._get_major_achievements(industry)
        }
        
        generated_summary = template.format(**summary_data)
        
        return {
            'generated_summary': generated_summary,
            'suggestions': self._get_summary_suggestions(user_data),
            'keywords_included': self._extract_keywords_from_summary(generated_summary),
            'tone_analysis': self._analyze_tone(generated_summary)
        }
    
    def enhance_work_experience(self, experiences: List[Dict]) -> List[Dict]:
        """Enhance work experience descriptions with AI"""
        enhanced_experiences = []
        
        for exp in experiences:
            enhanced_exp = exp.copy()
            
            # Enhance job description
            if 'description' in exp:
                enhanced_desc = self._enhance_job_description(exp['description'])
                enhanced_exp['enhanced_description'] = enhanced_desc
            
            # Generate achievement suggestions
            enhanced_exp['achievement_suggestions'] = self._generate_achievement_suggestions(exp)
            
            # Suggest quantification opportunities
            enhanced_exp['quantification_suggestions'] = self._suggest_quantifications(exp)
            
            enhanced_experiences.append(enhanced_exp)
        
        return enhanced_experiences
    
    def generate_skills_recommendations(self, current_skills: List[str], target_role: str, industry: str) -> Dict:
        """Generate skill recommendations based on role and industry"""
        # Get industry-specific keywords
        industry_skills = self.industry_keywords.get(industry.lower(), [])
        
        # Generate skill categories
        recommendations = {
            'technical_skills': self._get_technical_skills(target_role, industry),
            'soft_skills': self._get_soft_skills(target_role),
            'industry_specific': industry_skills,
            'trending_skills': self._get_trending_skills(industry),
            'skill_gaps': self._identify_skill_gaps(current_skills, target_role, industry),
            'priority_skills': self._get_priority_skills(target_role, industry)
        }
        
        return recommendations
    
    def generate_interview_questions(self, resume_data: Dict, job_description: str = None) -> List[Dict]:
        """Generate likely interview questions based on resume and job description"""
        questions = []
        
        # Experience-based questions
        if 'experiences' in resume_data:
            for exp in resume_data['experiences'][:3]:  # Top 3 experiences
                questions.extend(self._generate_experience_questions(exp))
        
        # Skill-based questions
        if 'skills' in resume_data:
            questions.extend(self._generate_skill_questions(resume_data['skills']))
        
        # Behavioral questions
        questions.extend(self._generate_behavioral_questions())
        
        # Job-specific questions if job description provided
        if job_description:
            questions.extend(self._generate_job_specific_questions(job_description))
        
        # Limit and randomize
        return random.sample(questions, min(len(questions), 15))
    
    def analyze_resume_completeness(self, resume_data: Dict) -> Dict:
        """Analyze resume completeness and provide improvement suggestions"""
        completeness_score = 0
        max_score = 100
        suggestions = []
        
        # Check essential sections
        essential_sections = {
            'personal_info': 15,
            'professional_summary': 15,
            'work_experience': 25,
            'education': 15,
            'skills': 15,
            'contact_info': 15
        }
        
        for section, points in essential_sections.items():
            if self._has_section_content(resume_data, section):
                completeness_score += points
            else:
                suggestions.append(f"Add {section.replace('_', ' ').title()} section")
        
        # Check optional but valuable sections
        optional_sections = {
            'projects': 5,
            'certifications': 5,
            'achievements': 5,
            'volunteer_experience': 3,
            'languages': 2
        }
        
        bonus_score = 0
        for section, points in optional_sections.items():
            if self._has_section_content(resume_data, section):
                bonus_score += points
        
        final_score = min(completeness_score + bonus_score, 100)
        
        return {
            'completeness_score': final_score,
            'suggestions': suggestions,
            'missing_sections': self._get_missing_sections(resume_data),
            'strength_areas': self._get_strength_areas(resume_data),
            'improvement_priority': self._prioritize_improvements(suggestions)
        }
    
    def _enhance_job_description(self, description: str) -> Dict:
        """Enhance job description with stronger language"""
        enhanced_bullets = []
        original_bullets = description.split('\n') if '\n' in description else [description]
        
        for bullet in original_bullets:
            if bullet.strip():
                enhanced = self._enhance_bullet_point(bullet.strip())
                enhanced_bullets.append(enhanced)
        
        return {
            'enhanced_description': '\n'.join([b['enhanced_text'] for b in enhanced_bullets]),
            'improvements': enhanced_bullets,
            'overall_improvement': sum([b['improvement_score'] for b in enhanced_bullets]) / len(enhanced_bullets) if enhanced_bullets else 0
        }
    
    def _enhance_bullet_point(self, bullet: str) -> Dict:
        """Enhance individual bullet point"""
        original = bullet
        enhanced = bullet
        improvements = []
        
        # Replace weak verbs with strong action words
        weak_patterns = [
            (r'^(responsible for|worked on|helped with)', 'Led'),
            (r'^(assisted|supported)', 'Collaborated on'),
            (r'^(participated in|involved in)', 'Contributed to'),
            (r'^(handled|dealt with)', 'Managed')
        ]
        
        for pattern, replacement in weak_patterns:
            if re.search(pattern, enhanced, re.IGNORECASE):
                enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
                improvements.append(f"Replaced weak verb with '{replacement}'")
        
        # Suggest quantification if missing
        has_numbers = bool(re.search(r'\d+[%$]?|\d+\s*(percent|dollars|users|customers|hours|days|months)', enhanced))
        if not has_numbers:
            improvements.append("Consider adding specific metrics or numbers")
        
        # Calculate improvement score
        original_score = self._score_bullet_point(original)
        enhanced_score = self._score_bullet_point(enhanced)
        improvement_score = enhanced_score - original_score
        
        return {
            'original_text': original,
            'enhanced_text': enhanced,
            'improvements': improvements,
            'improvement_score': improvement_score,
            'suggestions': self._get_bullet_suggestions(enhanced)
        }
    
    def _score_bullet_point(self, bullet: str) -> int:
        """Score bullet point quality (0-100)"""
        score = 0
        
        # Action word bonus
        action_words = [word for category in self.action_word_categories.values() for word in category]
        if any(word in bullet.lower() for word in action_words):
            score += 25
        
        # Quantification bonus
        if re.search(r'\d+[%$]?|\d+\s*(percent|dollars|users|customers)', bullet):
            score += 30
        
        # Length check (50-150 characters ideal)
        if 50 <= len(bullet) <= 150:
            score += 20
        elif len(bullet) > 150:
            score += 10
        
        # Specificity bonus
        specific_words = ['increased', 'decreased', 'improved', 'reduced', 'achieved', 'delivered']
        if any(word in bullet.lower() for word in specific_words):
            score += 15
        
        # Weak word penalty
        weak_words = ['responsible for', 'worked on', 'helped with', 'assisted']
        if any(weak in bullet.lower() for weak in weak_words):
            score -= 20
        
        return max(0, min(100, score))
    
    def _get_focus_area(self, industry: str) -> str:
        focus_areas = {
            'technology': 'innovation and problem-solving',
            'marketing': 'data-driven marketing strategies',
            'finance': 'financial analysis and risk management',
            'healthcare': 'patient care and quality improvement',
            'sales': 'revenue growth and client relationships'
        }
        return focus_areas.get(industry.lower(), 'professional excellence')
    
    def _get_strength_area(self, skills: List[str]) -> str:
        if not skills:
            return 'technical expertise'
        
        # Categorize skills
        if any(skill.lower() in ['python', 'java', 'javascript', 'programming'] for skill in skills):
            return 'technical programming skills'
        elif any(skill.lower() in ['marketing', 'seo', 'analytics'] for skill in skills):
            return 'digital marketing expertise'
        else:
            return f'{skills[0]} expertise'
    
    def _get_career_goal(self, industry: str) -> str:
        goals = {
            'technology': 'innovative technology solutions',
            'marketing': 'impactful marketing campaigns',
            'finance': 'strategic financial growth',
            'healthcare': 'improved patient outcomes',
            'sales': 'revenue growth and market expansion'
        }
        return goals.get(industry.lower(), 'organizational success')
    
    def _get_achievement_area(self, industry: str) -> str:
        achievements = {
            'technology': 'software development and system optimization',
            'marketing': 'campaign management and brand growth',
            'finance': 'financial planning and analysis',
            'healthcare': 'patient care and process improvement',
            'sales': 'sales performance and client acquisition'
        }
        return achievements.get(industry.lower(), 'project delivery and team collaboration')
    
    def _get_capability_phrase(self, industry: str) -> str:
        capabilities = {
            'technology': 'deliver scalable solutions and drive technical innovation',
            'marketing': 'execute data-driven campaigns and increase brand engagement',
            'finance': 'optimize financial performance and mitigate risks',
            'healthcare': 'improve patient satisfaction and operational efficiency',
            'sales': 'exceed targets and build lasting client relationships'
        }
        return capabilities.get(industry.lower(), 'drive results and exceed expectations')
    
    def _get_specialization(self, industry: str) -> str:
        specializations = {
            'technology': 'software architecture and development',
            'marketing': 'digital strategy and analytics',
            'finance': 'financial modeling and analysis',
            'healthcare': 'clinical excellence and patient care',
            'sales': 'strategic sales and business development'
        }
        return specializations.get(industry.lower(), 'strategic leadership and execution')
    
    def _get_major_achievements(self, industry: str) -> str:
        achievements = {
            'technology': 'delivering enterprise-scale solutions and leading digital transformation initiatives',
            'marketing': 'driving multi-million dollar campaigns and achieving record engagement rates',
            'finance': 'managing complex portfolios and delivering consistent ROI improvements',
            'healthcare': 'improving patient outcomes and implementing quality improvement programs',
            'sales': 'consistently exceeding quotas and building high-performing sales teams'
        }
        return achievements.get(industry.lower(), 'leading cross-functional teams and delivering exceptional results')
    
    def _get_summary_suggestions(self, user_data: Dict) -> List[str]:
        """Generate suggestions for improving professional summary"""
        suggestions = []
        
        if not user_data.get('achievements'):
            suggestions.append("Include 1-2 key achievements or accomplishments")
        
        if not user_data.get('target_role'):
            suggestions.append("Specify your target role or career objective")
        
        if len(user_data.get('skills', [])) < 3:
            suggestions.append("Highlight 3-5 key skills relevant to your target role")
        
        suggestions.append("Keep summary concise (3-4 sentences)")
        suggestions.append("Use industry-specific keywords")
        
        return suggestions
    
    def _extract_keywords_from_summary(self, summary: str) -> List[str]:
        """Extract important keywords from generated summary"""
        # Simple keyword extraction - in production, use more sophisticated NLP
        words = re.findall(r'\b[a-zA-Z]{4,}\b', summary.lower())
        
        # Filter out common words
        common_words = {'with', 'years', 'experience', 'skilled', 'proven', 'track', 'record'}
        keywords = [word for word in set(words) if word not in common_words]
        
        return keywords[:10]
    
    def _analyze_tone(self, text: str) -> Dict:
        """Analyze tone of the text"""
        # Simple tone analysis - in production, use sentiment analysis libraries
        confident_words = ['proven', 'expert', 'accomplished', 'successful', 'achieved']
        professional_words = ['experience', 'skilled', 'proficient', 'demonstrated', 'track record']
        
        confident_score = sum(1 for word in confident_words if word in text.lower())
        professional_score = sum(1 for word in professional_words if word in text.lower())
        
        return {
            'confidence_level': min(confident_score * 20, 100),
            'professionalism_level': min(professional_score * 20, 100),
            'overall_tone': 'confident and professional' if confident_score > 2 and professional_score > 2 else 'professional'
        }
    
    def _generate_achievement_suggestions(self, experience: Dict) -> List[str]:
        """Generate achievement suggestions for work experience"""
        suggestions = []
        role = experience.get('position', '').lower()
        
        if 'manager' in role or 'lead' in role:
            suggestions.extend([
                "Quantify team size managed or projects led",
                "Include budget or resource management achievements",
                "Highlight process improvements or efficiency gains"
            ])
        
        if 'developer' in role or 'engineer' in role:
            suggestions.extend([
                "Mention specific technologies or frameworks used",
                "Include performance improvements or optimization results",
                "Highlight successful project deliveries or launches"
            ])
        
        if 'sales' in role or 'account' in role:
            suggestions.extend([
                "Include quota achievement percentages",
                "Mention revenue generated or deals closed",
                "Highlight client retention or satisfaction metrics"
            ])
        
        # General suggestions
        suggestions.extend([
            "Add specific metrics (percentages, dollar amounts, timeframes)",
            "Include awards, recognition, or promotions received",
            "Mention cost savings or revenue generation"
        ])
        
        return suggestions[:5]
    
    def _suggest_quantifications(self, experience: Dict) -> List[str]:
        """Suggest specific quantification opportunities"""
        return [
            "Add percentage improvements (e.g., '25% increase in efficiency')",
            "Include team or project scale (e.g., 'managed team of 8 developers')",
            "Specify timeframes (e.g., 'delivered project 2 weeks ahead of schedule')",
            "Add budget or revenue figures (e.g., 'managed $2M budget')",
            "Include customer or user metrics (e.g., 'served 500+ clients daily')"
        ]
    
    def _get_technical_skills(self, role: str, industry: str) -> List[str]:
        """Get recommended technical skills"""
        role_skills = {
            'developer': ['Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'Git', 'AWS'],
            'data scientist': ['Python', 'R', 'SQL', 'Machine Learning', 'Pandas', 'Scikit-learn', 'Tableau'],
            'marketing': ['Google Analytics', 'SEO', 'SEM', 'Social Media', 'Email Marketing', 'CRM'],
            'project manager': ['Agile', 'Scrum', 'JIRA', 'MS Project', 'Risk Management', 'Stakeholder Management']
        }
        
        return role_skills.get(role.lower(), ['Microsoft Office', 'Project Management', 'Data Analysis'])
    
    def _get_soft_skills(self, role: str) -> List[str]:
        """Get recommended soft skills"""
        if 'manager' in role.lower() or 'lead' in role.lower():
            return ['Leadership', 'Team Management', 'Strategic Planning', 'Communication', 'Problem Solving']
        else:
            return ['Communication', 'Problem Solving', 'Teamwork', 'Adaptability', 'Time Management']
    
    def _get_trending_skills(self, industry: str) -> List[str]:
        """Get trending skills for industry"""
        trending = {
            'technology': ['AI/ML', 'Cloud Computing', 'DevOps', 'Cybersecurity', 'Blockchain'],
            'marketing': ['Marketing Automation', 'Data Analytics', 'Content Strategy', 'Social Media Marketing'],
            'finance': ['Financial Modeling', 'Risk Analysis', 'Regulatory Compliance', 'Data Analytics']
        }
        return trending.get(industry.lower(), ['Digital Literacy', 'Data Analysis', 'Project Management'])
    
    def _identify_skill_gaps(self, current_skills: List[str], target_role: str, industry: str) -> List[str]:
        """Identify skill gaps for target role"""
        recommended_skills = self._get_technical_skills(target_role, industry)
        current_skills_lower = [skill.lower() for skill in current_skills]
        
        gaps = [skill for skill in recommended_skills 
                if skill.lower() not in current_skills_lower]
        
        return gaps[:5]
    
    def _get_priority_skills(self, target_role: str, industry: str) -> List[str]:
        """Get high-priority skills for role and industry"""
        priority_skills = {
            ('developer', 'technology'): ['Python', 'JavaScript', 'React', 'SQL', 'Git'],
            ('marketing', 'technology'): ['Google Analytics', 'SEO', 'Content Marketing', 'Social Media'],
            ('manager', 'any'): ['Leadership', 'Project Management', 'Strategic Planning', 'Team Building']
        }
        
        key = (target_role.lower(), industry.lower())
        if key in priority_skills:
            return priority_skills[key]
        
        # Default priority skills
        return ['Communication', 'Problem Solving', 'Leadership', 'Technical Skills', 'Project Management']
    
    def _generate_experience_questions(self, experience: Dict) -> List[Dict]:
        """Generate interview questions based on work experience"""
        questions = []
        company = experience.get('company_name', 'your previous company')
        role = experience.get('position', 'your role')
        
        questions.extend([
            {
                'question': f"Tell me about your experience as {role} at {company}.",
                'category': 'experience',
                'difficulty': 'basic',
                'tips': 'Use the STAR method to structure your answer'
            },
            {
                'question': f"What was your biggest achievement in your role as {role}?",
                'category': 'achievement',
                'difficulty': 'intermediate',
                'tips': 'Quantify your achievement with specific metrics'
            },
            {
                'question': f"Describe a challenging situation you faced at {company} and how you handled it.",
                'category': 'problem_solving',
                'difficulty': 'intermediate',
                'tips': 'Focus on your problem-solving process and the positive outcome'
            }
        ])
        
        return questions
    
    def _generate_skill_questions(self, skills: List[str]) -> List[Dict]:
        """Generate questions based on skills"""
        questions = []
        
        for skill in skills[:3]:  # Top 3 skills
            questions.append({
                'question': f"How have you applied your {skill} skills in your previous roles?",
                'category': 'technical',
                'difficulty': 'intermediate',
                'tips': f'Provide specific examples of using {skill} to solve problems or achieve results'
            })
        
        return questions
    
    def _generate_behavioral_questions(self) -> List[Dict]:
        """Generate common behavioral interview questions"""
        return [
            {
                'question': "Tell me about a time when you had to work with a difficult team member.",
                'category': 'behavioral',
                'difficulty': 'intermediate',
                'tips': 'Focus on your communication and conflict resolution skills'
            },
            {
                'question': "Describe a situation where you had to meet a tight deadline.",
                'category': 'behavioral',
                'difficulty': 'basic',
                'tips': 'Highlight your time management and prioritization skills'
            },
            {
                'question': "Give me an example of when you showed leadership.",
                'category': 'behavioral',
                'difficulty': 'intermediate',
                'tips': 'Even if you weren\'t in a formal leadership role, show initiative and influence'
            }
        ]
    
    def _generate_job_specific_questions(self, job_description: str) -> List[Dict]:
        """Generate questions based on job description"""
        # Simple keyword extraction for question generation
        questions = []
        
        if 'team' in job_description.lower():
            questions.append({
                'question': "How do you handle working in a team environment?",
                'category': 'teamwork',
                'difficulty': 'basic',
                'tips': 'Emphasize collaboration and communication skills'
            })
        
        if 'leadership' in job_description.lower():
            questions.append({
                'question': "Describe your leadership style and give an example.",
                'category': 'leadership',
                'difficulty': 'intermediate',
                'tips': 'Adapt your leadership style to the situation and team needs'
            })
        
        return questions
    
    def _has_section_content(self, resume_data: Dict, section: str) -> bool:
        """Check if resume has content for a specific section"""
        section_mappings = {
            'personal_info': ['full_name', 'email', 'phone'],
            'professional_summary': ['professional_summary'],
            'work_experience': ['work_experiences', 'experiences'],
            'education': ['educations', 'education'],
            'skills': ['skills'],
            'contact_info': ['email', 'phone'],
            'projects': ['projects'],
            'certifications': ['certifications'],
            'achievements': ['achievements'],
            'volunteer_experience': ['volunteer_experiences'],
            'languages': ['languages']
        }
        
        fields = section_mappings.get(section, [section])
        
        for field in fields:
            if field in resume_data and resume_data[field]:
                if isinstance(resume_data[field], list):
                    return len(resume_data[field]) > 0
                elif isinstance(resume_data[field], str):
                    return len(resume_data[field].strip()) > 0
                else:
                    return bool(resume_data[field])
        
        return False
    
    def _get_missing_sections(self, resume_data: Dict) -> List[str]:
        """Get list of missing important sections"""
        important_sections = ['personal_info', 'professional_summary', 'work_experience', 'education', 'skills']
        missing = []
        
        for section in important_sections:
            if not self._has_section_content(resume_data, section):
                missing.append(section.replace('_', ' ').title())
        
        return missing
    
    def _get_strength_areas(self, resume_data: Dict) -> List[str]:
        """Identify strength areas of the resume"""
        strengths = []
        
        if self._has_section_content(resume_data, 'work_experience'):
            experiences = resume_data.get('work_experiences', resume_data.get('experiences', []))
            if len(experiences) >= 3:
                strengths.append('Strong work experience')
        
        if self._has_section_content(resume_data, 'skills'):
            skills = resume_data.get('skills', [])
            if len(skills) >= 5:
                strengths.append('Comprehensive skill set')
        
        if self._has_section_content(resume_data, 'education'):
            strengths.append('Educational background')
        
        if self._has_section_content(resume_data, 'certifications'):
            strengths.append('Professional certifications')
        
        return strengths
    
    def _prioritize_improvements(self, suggestions: List[str]) -> List[str]:
        """Prioritize improvement suggestions"""
        priority_order = [
            'professional summary',
            'work experience',
            'skills',
            'education',
            'personal info',
            'contact info'
        ]
        
        prioritized = []
        for priority in priority_order:
            for suggestion in suggestions:
                if priority in suggestion.lower() and suggestion not in prioritized:
                    prioritized.append(suggestion)
        
        # Add remaining suggestions
        for suggestion in suggestions:
            if suggestion not in prioritized:
                prioritized.append(suggestion)
        
        return prioritized
    
    def _get_bullet_suggestions(self, bullet: str) -> List[str]:
        """Get specific suggestions for improving a bullet point"""
        suggestions = []
        
        if not re.search(r'\d+', bullet):
            suggestions.append("Add specific numbers or percentages")
        
        if len(bullet) < 50:
            suggestions.append("Expand with more specific details")
        elif len(bullet) > 150:
            suggestions.append("Make more concise while keeping key details")
        
        if not any(word in bullet.lower() for word in ['achieved', 'improved', 'increased', 'delivered']):
            suggestions.append("Start with a strong action verb")
        
        return suggestions
