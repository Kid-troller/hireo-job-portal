from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
import json
import re
from datetime import datetime, timedelta
from .models import *
from .ats_engine import ATSOptimizationEngine
from .resume_ai import ResumeAI
from .resume_export import ResumeExportEngine, create_export_response, get_content_type
from .decorators import jobseeker_required

# Initialize AI engines
ats_engine = ATSOptimizationEngine()
resume_ai = ResumeAI()

@login_required
@jobseeker_required
def resume_builder_dashboard(request):
    """Main resume builder dashboard with wizard interface"""
    user_profile = request.user.userprofile
    resumes = Resume.objects.filter(user_profile=user_profile).order_by('-updated_at')
    
    # Get recent activity
    recent_exports = ResumeExport.objects.filter(
        resume__user_profile=user_profile
    ).order_by('-created_at')[:5]
    
    # Get analytics summary
    total_resumes = resumes.count()
    total_versions = ResumeVersion.objects.filter(
        base_resume__user_profile=user_profile
    ).count()
    
    avg_ats_score = 0
    if resumes.exists():
        ats_optimizations = ATSOptimization.objects.filter(
            resume__user_profile=user_profile
        )
        if ats_optimizations.exists():
            avg_ats_score = sum(opt.overall_ats_score for opt in ats_optimizations) / ats_optimizations.count()
    
    context = {
        'resumes': resumes,
        'recent_exports': recent_exports,
        'total_resumes': total_resumes,
        'total_versions': total_versions,
        'avg_ats_score': round(avg_ats_score, 1),
        'templates': ResumeTemplate.objects.filter(is_active=True).order_by('-ats_score'),
    }
    return render(request, 'accounts/resume_builder_dashboard.html', context)

@login_required
@jobseeker_required
def resume_wizard(request, resume_id=None):
    """Step-by-step resume creation wizard"""
    user_profile = request.user.userprofile
    
    if resume_id:
        resume = get_object_or_404(Resume, id=resume_id, user_profile=user_profile)
    else:
        resume = None
    
    # Get wizard step from URL parameter
    step = request.GET.get('step', '1')
    
    context = {
        'resume': resume,
        'current_step': step,
        'templates': ResumeTemplate.objects.filter(is_active=True).order_by('-ats_score'),
        'user_profile': user_profile,
    }
    
    return render(request, 'accounts/resume_wizard.html', context)

@login_required
@jobseeker_required
@require_POST
def create_resume(request):
    """Create new resume from wizard"""
    user_profile = request.user.userprofile
    
    try:
        data = json.loads(request.body)
        
        with transaction.atomic():
            # Create resume
            resume = Resume.objects.create(
                user_profile=user_profile,
                title=data.get('title', 'My Resume'),
                template=data.get('template', 'modern-clean'),
                color_scheme=data.get('color_scheme', 'blue'),
                font_family=data.get('font_family', 'arial'),
                full_name=data.get('full_name', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                address=data.get('address', ''),
                professional_summary=data.get('professional_summary', ''),
                section_order=data.get('section_order', [
                    'personal_info', 'professional_summary', 'work_experience', 
                    'education', 'skills', 'projects', 'certifications'
                ])
            )
            
            # Create work experiences
            for exp_data in data.get('work_experiences', []):
                ResumeWorkExperience.objects.create(
                    resume=resume,
                    company_name=exp_data.get('company_name', ''),
                    position=exp_data.get('position', ''),
                    location=exp_data.get('location', ''),
                    start_date=datetime.strptime(exp_data.get('start_date'), '%Y-%m-%d').date(),
                    end_date=datetime.strptime(exp_data.get('end_date'), '%Y-%m-%d').date() if exp_data.get('end_date') else None,
                    is_current=exp_data.get('is_current', False),
                    description=exp_data.get('description', ''),
                    order=exp_data.get('order', 0)
                )
            
            # Create education entries
            for edu_data in data.get('educations', []):
                ResumeEducation.objects.create(
                    resume=resume,
                    institution=edu_data.get('institution', ''),
                    degree_type=edu_data.get('degree_type', 'bachelor'),
                    field_of_study=edu_data.get('field_of_study', ''),
                    location=edu_data.get('location', ''),
                    start_date=datetime.strptime(edu_data.get('start_date'), '%Y-%m-%d').date(),
                    end_date=datetime.strptime(edu_data.get('end_date'), '%Y-%m-%d').date() if edu_data.get('end_date') else None,
                    gpa=float(edu_data.get('gpa')) if edu_data.get('gpa') else None,
                    description=edu_data.get('description', ''),
                    order=edu_data.get('order', 0)
                )
            
            # Create skills
            for skill_data in data.get('skills', []):
                ResumeSkill.objects.create(
                    resume=resume,
                    name=skill_data.get('name', ''),
                    level=skill_data.get('level', 'intermediate'),
                    category=skill_data.get('category', 'technical'),
                    years_experience=int(skill_data.get('years_experience', 0)) if skill_data.get('years_experience') else None,
                    order=skill_data.get('order', 0)
                )
            
            # Run initial ATS analysis
            _run_ats_analysis(resume)
            
        return JsonResponse({
            'success': True,
            'resume_id': resume.id,
            'message': 'Resume created successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@jobseeker_required
def job_description_analyzer(request):
    """Analyze job descriptions for ATS optimization"""
    user_profile = request.user.userprofile
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            job_text = data.get('job_description', '')
            
            if not job_text:
                return JsonResponse({'error': 'Job description is required'}, status=400)
            
            # Analyze job description
            analysis = ats_engine.analyze_job_description(job_text)
            
            # Save job description
            job_desc = JobDescription.objects.create(
                user_profile=user_profile,
                title=data.get('title', 'Analyzed Job'),
                company=data.get('company', ''),
                description=job_text,
                requirements=data.get('requirements', ''),
                extracted_keywords=analysis['extracted_keywords'],
                required_skills=analysis['required_skills'],
                preferred_skills=analysis['preferred_skills'],
                experience_level=analysis['experience_level'],
                education_requirements=analysis['education_requirements'],
                keyword_count=analysis['keyword_count'],
                analysis_score=analysis['analysis_score']
            )
            
            return JsonResponse({
                'success': True,
                'job_id': job_desc.id,
                'analysis': analysis
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show analyzer interface
    job_descriptions = JobDescription.objects.filter(
        user_profile=user_profile
    ).order_by('-created_at')[:10]
    
    context = {
        'job_descriptions': job_descriptions,
    }
    return render(request, 'accounts/job_description_analyzer.html', context)

@login_required
@jobseeker_required
def ats_optimization(request, resume_id):
    """ATS optimization analysis and suggestions"""
    user_profile = request.user.userprofile
    resume = get_object_or_404(Resume, id=resume_id, user_profile=user_profile)
    
    # Get or create ATS optimization
    ats_opt, created = ATSOptimization.objects.get_or_create(resume=resume)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            job_description_id = data.get('job_description_id')
            
            if job_description_id:
                job_desc = get_object_or_404(
                    JobDescription, 
                    id=job_description_id, 
                    user_profile=user_profile
                )
                ats_opt.job_description = job_desc
            
            # Run ATS analysis
            _run_ats_analysis(resume, ats_opt.job_description)
            
            return JsonResponse({
                'success': True,
                'message': 'ATS analysis updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # Generate resume content for analysis
    resume_content = _generate_resume_text(resume)
    
    # Get keyword gap analysis if job description exists
    keyword_gaps = {}
    if ats_opt.job_description:
        keyword_gaps = ats_engine.analyze_keyword_gaps(
            resume_content, 
            ats_opt.job_description.extracted_keywords
        )
    
    context = {
        'resume': resume,
        'ats_optimization': ats_opt,
        'keyword_gaps': keyword_gaps,
        'job_descriptions': JobDescription.objects.filter(user_profile=user_profile),
    }
    return render(request, 'accounts/ats_optimization.html', context)

@login_required
@jobseeker_required
def ai_bullet_enhancer(request, resume_id):
    """AI-powered bullet point enhancement"""
    user_profile = request.user.userprofile
    resume = get_object_or_404(Resume, id=resume_id, user_profile=user_profile)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'enhance_bullets':
                # Get all bullet points from work experiences
                experiences = resume.work_experiences.all()
                enhanced_bullets = []
                
                for exp in experiences:
                    if exp.description:
                        bullets = exp.description.split('\n')
                        bullets = [b.strip() for b in bullets if b.strip()]
                        
                        enhanced = ats_engine.enhance_bullet_points(bullets)
                        
                        for i, enhancement in enumerate(enhanced):
                            # Save AI enhancement
                            ai_bullet, created = AIBulletPoint.objects.get_or_create(
                                resume=resume,
                                section_type='experience',
                                original_text=enhancement['original_text'],
                                defaults={
                                    'enhanced_text': enhancement['enhanced_text'],
                                    'improvements_made': enhancement['improvements_made'],
                                    'original_score': enhancement['original_score'],
                                    'enhanced_score': enhancement['enhanced_score'],
                                    'improvement_percentage': enhancement['improvement_percentage']
                                }
                            )
                            enhanced_bullets.append(ai_bullet)
                
                return JsonResponse({
                    'success': True,
                    'enhanced_count': len(enhanced_bullets),
                    'message': f'Enhanced {len(enhanced_bullets)} bullet points!'
                })
            
            elif action == 'apply_enhancement':
                bullet_id = data.get('bullet_id')
                ai_bullet = get_object_or_404(AIBulletPoint, id=bullet_id, resume=resume)
                
                # Apply enhancement to the actual resume
                # This would update the work experience description
                ai_bullet.is_applied = True
                ai_bullet.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Enhancement applied successfully!'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show enhancement interface
    ai_bullets = AIBulletPoint.objects.filter(resume=resume).order_by('-enhanced_score')
    
    context = {
        'resume': resume,
        'ai_bullets': ai_bullets,
    }
    return render(request, 'accounts/ai_bullet_enhancer.html', context)

@login_required
@jobseeker_required
def resume_versions(request, resume_id):
    """Manage multiple resume versions"""
    user_profile = request.user.userprofile
    base_resume = get_object_or_404(Resume, id=resume_id, user_profile=user_profile)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'create_version':
                version = ResumeVersion.objects.create(
                    base_resume=base_resume,
                    version_name=data.get('version_name', f'Version {base_resume.versions.count() + 1}'),
                    description=data.get('description', ''),
                    tailored_summary=data.get('tailored_summary', ''),
                    emphasized_skills=data.get('emphasized_skills', []),
                    reordered_sections=data.get('reordered_sections', [])
                )
                
                if data.get('job_description_id'):
                    job_desc = get_object_or_404(
                        JobDescription, 
                        id=data.get('job_description_id'),
                        user_profile=user_profile
                    )
                    version.job_description = job_desc
                    version.save()
                
                return JsonResponse({
                    'success': True,
                    'version_id': version.id,
                    'message': 'Resume version created successfully!'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    versions = base_resume.versions.all().order_by('-updated_at')
    job_descriptions = JobDescription.objects.filter(user_profile=user_profile)
    
    context = {
        'base_resume': base_resume,
        'versions': versions,
        'job_descriptions': job_descriptions,
    }
    return render(request, 'accounts/resume_versions.html', context)

@login_required
@jobseeker_required
def resume_comparison(request):
    """Compare different resume versions"""
    user_profile = request.user.userprofile
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            resume_a_id = data.get('resume_a_id')
            resume_b_id = data.get('resume_b_id')
            
            resume_a = get_object_or_404(Resume, id=resume_a_id, user_profile=user_profile)
            resume_b = get_object_or_404(Resume, id=resume_b_id, user_profile=user_profile)
            
            # Get ATS scores for comparison
            ats_a = ATSOptimization.objects.filter(resume=resume_a).first()
            ats_b = ATSOptimization.objects.filter(resume=resume_b).first()
            
            ats_score_a = ats_a.overall_ats_score if ats_a else 0
            ats_score_b = ats_b.overall_ats_score if ats_b else 0
            
            # Create comparison
            comparison = ResumeComparison.objects.create(
                user_profile=user_profile,
                resume_a=resume_a,
                resume_b=resume_b,
                ats_score_diff=ats_score_b - ats_score_a,
                keyword_match_diff=0,  # Calculate based on analysis
                content_quality_diff=0,  # Calculate based on analysis
                improvements_found=_find_improvements(resume_a, resume_b),
                regressions_found=_find_regressions(resume_a, resume_b),
                recommendations=_generate_comparison_recommendations(resume_a, resume_b)
            )
            
            return JsonResponse({
                'success': True,
                'comparison_id': comparison.id,
                'redirect_url': f'/accounts/resume-comparison/{comparison.id}/'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    resumes = Resume.objects.filter(user_profile=user_profile)
    recent_comparisons = ResumeComparison.objects.filter(
        user_profile=user_profile
    ).order_by('-created_at')[:5]
    
    context = {
        'resumes': resumes,
        'recent_comparisons': recent_comparisons,
    }
    return render(request, 'accounts/resume_comparison.html', context)

@login_required
@jobseeker_required
def job_application_tracker(request):
    """Track job applications with resume versions"""
    user_profile = request.user.userprofile
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create job application tracker entry
            application = JobApplicationTracker.objects.create(
                user_profile=user_profile,
                company_name=data.get('company_name', ''),
                position_title=data.get('position_title', ''),
                application_url=data.get('application_url', ''),
                status=data.get('status', 'applied'),
                notes=data.get('notes', ''),
                resume_ats_score=data.get('resume_ats_score', 0)
            )
            
            # Link job description if provided
            if data.get('job_description_id'):
                job_desc = get_object_or_404(
                    JobDescription,
                    id=data.get('job_description_id'),
                    user_profile=user_profile
                )
                application.job_description = job_desc
                application.save()
            
            return JsonResponse({
                'success': True,
                'application_id': application.id,
                'message': 'Job application tracked successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show tracker dashboard
    applications = JobApplicationTracker.objects.filter(
        user_profile=user_profile
    ).order_by('-applied_date')
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_applications = applications.count()
    responses = applications.exclude(status='applied').count()
    interviews = applications.filter(status__in=['interview_scheduled', 'interviewed']).count()
    offers = applications.filter(status='offer_received').count()
    
    response_rate = (responses / total_applications * 100) if total_applications > 0 else 0
    interview_rate = (interviews / total_applications * 100) if total_applications > 0 else 0
    
    context = {
        'applications': page_obj,
        'total_applications': total_applications,
        'responses': responses,
        'interviews': interviews,
        'offers': offers,
        'response_rate': round(response_rate, 1),
        'interview_rate': round(interview_rate, 1),
        'resumes': Resume.objects.filter(user_profile=user_profile),
        'job_descriptions': JobDescription.objects.filter(user_profile=user_profile),
    }
    return render(request, 'accounts/job_application_tracker.html', context)

@login_required
@jobseeker_required
def cover_letter_builder(request):
    """AI-assisted cover letter builder"""
    user_profile = request.user.userprofile
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            cover_letter = CoverLetter.objects.create(
                user_profile=user_profile,
                title=data.get('title', 'Cover Letter'),
                content=data.get('content', '')
            )
            
            # Link resume and job description if provided
            if data.get('resume_id'):
                resume = get_object_or_404(Resume, id=data.get('resume_id'), user_profile=user_profile)
                cover_letter.resume = resume
            
            if data.get('job_description_id'):
                job_desc = get_object_or_404(JobDescription, id=data.get('job_description_id'), user_profile=user_profile)
                cover_letter.job_description = job_desc
            
            # Generate AI suggestions
            ai_suggestions = _generate_cover_letter_suggestions(cover_letter)
            cover_letter.ai_suggestions = ai_suggestions
            cover_letter.save()
            
            return JsonResponse({'success': True, 'message': 'Cover letter created successfully'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    cover_letters = CoverLetter.objects.filter(user_profile=user_profile).order_by('-updated_at')
    resumes = Resume.objects.filter(user_profile=user_profile)
    job_descriptions = JobDescription.objects.filter(user_profile=user_profile)
    
    context = {
        'cover_letters': cover_letters,
        'resumes': resumes,
        'job_descriptions': job_descriptions,
    }
    return render(request, 'accounts/cover_letter_builder.html', context)

# Helper functions
def _run_ats_analysis(resume, job_description=None):
    """Run comprehensive ATS analysis on resume"""
    # Generate resume text content
    resume_content = _generate_resume_text(resume)
    
    # Get job description text if provided
    job_text = job_description.description if job_description else None
    
    # Calculate ATS scores
    scores = ats_engine.calculate_ats_score(resume_content, job_text)
    
    # Get or create ATS optimization record
    ats_opt, created = ATSOptimization.objects.get_or_create(
        resume=resume,
        defaults={'job_description': job_description}
    )
    
    # Update scores
    ats_opt.overall_ats_score = scores['overall_ats_score']
    ats_opt.keyword_match_score = scores['keyword_match_score']
    ats_opt.formatting_score = scores['formatting_score']
    ats_opt.content_relevance_score = scores['content_relevance_score']
    
    if job_description:
        # Analyze keyword gaps
        keyword_analysis = ats_engine.analyze_keyword_gaps(
            resume_content, 
            job_description.extracted_keywords
        )
        ats_opt.matched_keywords = keyword_analysis['matched_keywords']
        ats_opt.missing_keywords = keyword_analysis['missing_keywords']
        ats_opt.keyword_density = keyword_analysis['keyword_density']
    
    ats_opt.save()
    return ats_opt

def _generate_resume_text(resume):
    """Generate plain text version of resume for analysis"""
    content = []
    
    # Personal info
    content.append(f"Name: {resume.full_name}")
    content.append(f"Email: {resume.email}")
    content.append(f"Phone: {resume.phone}")
    if resume.address:
        content.append(f"Address: {resume.address}")
    
    # Professional summary
    if resume.professional_summary:
        content.append("\nProfessional Summary:")
        content.append(resume.professional_summary)
    
    # Work experience
    experiences = resume.work_experiences.all().order_by('-start_date')
    if experiences:
        content.append("\nWork Experience:")
        for exp in experiences:
            content.append(f"{exp.position} at {exp.company_name}")
            if exp.description:
                content.append(exp.description)
    
    # Education
    educations = resume.educations.all().order_by('-start_date')
    if educations:
        content.append("\nEducation:")
        for edu in educations:
            content.append(f"{edu.degree_type} in {edu.field_of_study} from {edu.institution}")
    
    # Skills
    skills = resume.skills.all()
    if skills:
        content.append("\nSkills:")
        skill_names = [skill.name for skill in skills]
        content.append(", ".join(skill_names))
    
    return "\n".join(content)

def _find_improvements(resume_a, resume_b):
    """Find improvements in resume B compared to resume A"""
    improvements = []
    
    # Compare ATS scores
    ats_a = ATSOptimization.objects.filter(resume=resume_a).first()
    ats_b = ATSOptimization.objects.filter(resume=resume_b).first()
    
    if ats_a and ats_b:
        if ats_b.overall_ats_score > ats_a.overall_ats_score:
            improvements.append(f"ATS score improved by {ats_b.overall_ats_score - ats_a.overall_ats_score} points")
    
    # Compare section counts
    if resume_b.work_experiences.count() > resume_a.work_experiences.count():
        improvements.append("Added more work experience entries")
    
    if resume_b.skills.count() > resume_a.skills.count():
        improvements.append("Added more skills")
    
    return improvements

def _find_regressions(resume_a, resume_b):
    """Find areas where resume B is worse than resume A"""
    regressions = []
    
    # Compare ATS scores
    ats_a = ATSOptimization.objects.filter(resume=resume_a).first()
    ats_b = ATSOptimization.objects.filter(resume=resume_b).first()
    
    if ats_a and ats_b:
        if ats_b.overall_ats_score < ats_a.overall_ats_score:
            regressions.append(f"ATS score decreased by {ats_a.overall_ats_score - ats_b.overall_ats_score} points")
    
    return regressions

def _generate_comparison_recommendations(resume_a, resume_b):
    """Generate recommendations based on resume comparison"""
    recommendations = []
    
    # Get the better performing resume
    ats_a = ATSOptimization.objects.filter(resume=resume_a).first()
    ats_b = ATSOptimization.objects.filter(resume=resume_b).first()
    
    if ats_a and ats_b:
        if ats_b.overall_ats_score > ats_a.overall_ats_score:
            recommendations.append(f"Use {resume_b.title} as your primary resume")
        else:
            recommendations.append(f"Use {resume_a.title} as your primary resume")
    
    recommendations.extend([
        "Continue optimizing for specific job descriptions",
        "Regularly update your resume with new achievements",
        "Test different templates for better ATS compatibility"
    ])
    
    return recommendations

def _generate_cover_letter_suggestions(cover_letter):
    """Generate AI suggestions for cover letter improvement"""
    suggestions = []
    
    content = cover_letter.content.lower()
    
    if len(cover_letter.content) < 200:
        suggestions.append("Consider expanding your cover letter to 250-400 words")
    
    if "dear hiring manager" in content:
        suggestions.append("Try to find the specific hiring manager's name for personalization")
    
    if not any(word in content for word in ['achieve', 'accomplish', 'deliver', 'improve']):
        suggestions.append("Include specific achievements and quantifiable results")
    
    if cover_letter.job_description:
        # Check for keyword alignment
        job_keywords = cover_letter.job_description.extracted_keywords
        content_words = content.split()
        
        missing_keywords = [kw for kw in job_keywords[:5] if kw.lower() not in content_words]
        if missing_keywords:
            suggestions.append(f"Consider including these job-relevant keywords: {', '.join(missing_keywords[:3])}")
    
    return suggestions


@login_required
@jobseeker_required
def export_resume(request, resume_id):
    """Export resume in specified format"""
    try:
        resume = Resume.objects.get(id=resume_id, user=request.user)
        format_type = request.GET.get('format', 'pdf').lower()
        template_name = request.GET.get('template')
        
        # Initialize export engine
        export_engine = ResumeExportEngine()
        
        # Export resume
        file_content, filename = export_engine.export_resume(
            resume, format_type, template_name
        )
        
        # Save to cloud storage if requested
        if request.GET.get('save_cloud', 'false').lower() == 'true':
            cloud_url = export_engine.save_to_cloud(
                file_content, filename, request.user.id
            )
            
            # Log export activity
            ResumeExport.objects.create(
                resume=resume,
                format=format_type.upper(),
                filename=filename,
                cloud_url=cloud_url,
                file_size=len(file_content)
            )
        
        # Return file response
        content_type = get_content_type(format_type)
        return create_export_response(file_content, filename, content_type)
        
    except Resume.DoesNotExist:
        return JsonResponse({'error': 'Resume not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@jobseeker_required
def export_history(request):
    """View export history and cloud storage"""
    export_engine = ResumeExportEngine()
    
    # Get export history from database
    db_exports = ResumeExport.objects.filter(
        resume__user=request.user
    ).select_related('resume').order_by('-created_at')[:20]
    
    # Get cloud storage history
    cloud_exports = export_engine.get_export_history(request.user.id)
    
    context = {
        'db_exports': db_exports,
        'cloud_exports': cloud_exports,
        'total_exports': db_exports.count(),
        'storage_used': sum(exp.file_size for exp in db_exports if exp.file_size)
    }
    
    return render(request, 'accounts/export_history.html', context)


@login_required
@jobseeker_required
def bulk_export(request):
    """Export multiple resumes in batch"""
    if request.method == 'POST':
        resume_ids = request.POST.getlist('resume_ids')
        format_type = request.POST.get('format', 'pdf')
        
        if not resume_ids:
            return JsonResponse({'error': 'No resumes selected'}, status=400)
        
        try:
            import zipfile
            from io import BytesIO
            
            # Create ZIP file
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                export_engine = ResumeExportEngine()
                
                for resume_id in resume_ids:
                    try:
                        resume = Resume.objects.get(id=resume_id, user=request.user)
                        file_content, filename = export_engine.export_resume(
                            resume, format_type
                        )
                        zip_file.writestr(filename, file_content)
                    except Resume.DoesNotExist:
                        continue
            
            zip_buffer.seek(0)
            
            # Return ZIP file
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="resumes_export.zip"'
            return response
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - show bulk export form
    resumes = Resume.objects.filter(user=request.user)
    return render(request, 'accounts/bulk_export.html', {'resumes': resumes})


@login_required
@jobseeker_required
def resume_analytics_dashboard(request):
    """Analytics dashboard for resume performance"""
    # Get user's resumes and analytics
    resumes = Resume.objects.filter(user=request.user)
    
    # Calculate analytics
    analytics_data = {
        'total_resumes': resumes.count(),
        'total_versions': ResumeVersion.objects.filter(resume__user=request.user).count(),
        'total_exports': ResumeExport.objects.filter(resume__user=request.user).count(),
        'avg_ats_score': 0,
        'top_keywords': [],
        'export_trends': {},
        'ats_improvements': []
    }
    
    if resumes.exists():
        # Calculate average ATS score
        ats_optimizations = ATSOptimization.objects.filter(resume__user=request.user)
        if ats_optimizations.exists():
            total_score = sum(opt.overall_score for opt in ats_optimizations if opt.overall_score)
            analytics_data['avg_ats_score'] = total_score / ats_optimizations.count()
        
        # Get top keywords from job descriptions
        job_descriptions = JobDescription.objects.filter(
            atsoptimization__resume__user=request.user
        ).distinct()
        
        keyword_counts = {}
        for jd in job_descriptions:
            if jd.extracted_keywords:
                for keyword in jd.extracted_keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        analytics_data['top_keywords'] = sorted(
            keyword_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        
        # Export trends (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        recent_exports = ResumeExport.objects.filter(
            resume__user=request.user,
            created_at__gte=thirty_days_ago
        ).values('created_at__date', 'format').order_by('created_at__date')
        
        # Group by date and format
        export_trends = {}
        for export in recent_exports:
            date_str = export['created_at__date'].strftime('%Y-%m-%d')
            if date_str not in export_trends:
                export_trends[date_str] = {'PDF': 0, 'DOCX': 0, 'TXT': 0, 'HTML': 0}
            export_trends[date_str][export['format']] += 1
        
        analytics_data['export_trends'] = export_trends
    
    return render(request, 'accounts/resume_analytics_dashboard.html', {
        'analytics': analytics_data,
        'resumes': resumes
    })
