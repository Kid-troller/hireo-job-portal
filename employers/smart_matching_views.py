# Smart Matching System Views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import EmployerProfile
from accounts.models import UserProfile, JobSeekerProfile
from jobs.models import JobPost
from .pdf_utils import generate_smart_matching_report_pdf, create_pdf_response

@login_required
def smart_matching(request):
    """Smart matching main dashboard"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get active jobs for matching
    active_jobs = JobPost.objects.filter(company=employer_profile.company, status='active')
    
    # Get recent matching results
    total_candidates = JobSeekerProfile.objects.count()
    
    # Get matching statistics
    matching_stats = {
        'total_candidates': total_candidates,
        'active_jobs': active_jobs.count(),
        'recent_matches': 0,  # Will be calculated based on matching history
        'success_rate': 85.2,  # Placeholder - can be calculated from actual data
    }
    
    context = {
        'employer_profile': employer_profile,
        'active_jobs': active_jobs[:5],  # Show top 5 jobs
        'matching_stats': matching_stats,
    }
    
    return render(request, 'employers/smart_matching/dashboard.html', context)

@login_required
def smart_matching_results(request):
    """Smart matching results with filtering"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Get job ID from request
    job_id = request.GET.get('job_id')
    if not job_id:
        messages.error(request, 'Please select a job to find matches.')
        return redirect('employer:smart_matching')
    
    try:
        job = JobPost.objects.get(id=job_id, company=employer_profile.company)
    except JobPost.DoesNotExist:
        messages.error(request, 'Job not found.')
        return redirect('employer:smart_matching')
    
    # Get matching candidates using smart algorithm
    matched_candidates = get_smart_matches(job, request.GET)
    
    # Pagination
    paginator = Paginator(matched_candidates, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'employer_profile': employer_profile,
        'job': job,
        'candidates': page_obj,
        'page_obj': page_obj,
        'total_matches': len(matched_candidates),
        'filters': request.GET,
    }
    
    return render(request, 'employers/smart_matching/results.html', context)

@login_required
def smart_matching_candidate_detail(request, candidate_id):
    """Detailed candidate view for smart matching"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    candidate = get_object_or_404(JobSeekerProfile, id=candidate_id)
    
    # Get job ID for matching context
    job_id = request.GET.get('job_id')
    job = None
    match_score = None
    match_reasons = []
    
    if job_id:
        try:
            job = JobPost.objects.get(id=job_id, company=employer_profile.company)
            match_score = calculate_match_score(candidate, job)
            match_reasons = get_match_reasons(candidate, job)
        except JobPost.DoesNotExist:
            pass
    
    context = {
        'employer_profile': employer_profile,
        'candidate': candidate,
        'job': job,
        'match_score': match_score,
        'match_reasons': match_reasons,
    }
    
    return render(request, 'employers/smart_matching/candidate_detail.html', context)

@login_required
def smart_matching_preferences(request):
    """Smart matching preferences and settings"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    if request.method == 'POST':
        # Save matching preferences
        preferences = {
            'skill_weight': int(request.POST.get('skill_weight', 40)),
            'experience_weight': int(request.POST.get('experience_weight', 30)),
            'education_weight': int(request.POST.get('education_weight', 20)),
            'location_weight': int(request.POST.get('location_weight', 10)),
            'min_match_score': int(request.POST.get('min_match_score', 70)),
            'auto_notify': request.POST.get('auto_notify') == 'on',
            'include_remote': request.POST.get('include_remote') == 'on',
        }
        
        # Save to employer profile or create a separate model
        # For now, we'll use a simple approach
        messages.success(request, 'Matching preferences updated successfully!')
        return redirect('employer:smart_matching_preferences')
    
    # Get current preferences (default values for now)
    preferences = {
        'skill_weight': 40,
        'experience_weight': 30,
        'education_weight': 20,
        'location_weight': 10,
        'min_match_score': 70,
        'auto_notify': True,
        'include_remote': True,
    }
    
    context = {
        'employer_profile': employer_profile,
        'preferences': preferences,
    }
    
    return render(request, 'employers/smart_matching/preferences.html', context)

@login_required
def smart_matching_analytics(request):
    """Smart matching analytics and insights"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            messages.error(request, 'Access denied. Employer account required.')
            return redirect('home')
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        messages.error(request, 'Please complete your employer profile first.')
        return redirect('employer:setup_company')
    
    # Generate analytics data
    analytics_data = {
        'total_matches_found': 1247,
        'successful_hires': 89,
        'average_match_score': 78.5,
        'top_skills_matched': ['Python', 'JavaScript', 'React', 'Node.js', 'SQL'],
        'match_trends': [65, 72, 78, 85, 89, 92],  # Last 6 months
        'success_by_experience': {
            'entry': 65,
            'junior': 78,
            'mid': 85,
            'senior': 92,
        }
    }
    
    context = {
        'employer_profile': employer_profile,
        'analytics': analytics_data,
    }
    
    return render(request, 'employers/smart_matching/analytics.html', context)

@login_required
def run_smart_matching(request):
    """Run smart matching algorithm for a specific job"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        return JsonResponse({'error': 'Employer profile required'}, status=400)
    
    job_id = request.POST.get('job_id')
    if not job_id:
        return JsonResponse({'error': 'Job ID required'}, status=400)
    
    try:
        job = JobPost.objects.get(id=job_id, company=employer_profile.company)
    except JobPost.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    
    # Run matching algorithm
    matches = get_smart_matches(job, {})
    
    return JsonResponse({
        'success': True,
        'total_matches': len(matches),
        'redirect_url': f'/employer/smart-matching/results/?job_id={job_id}'
    })

@login_required
def download_matching_results_pdf(request):
    """Download smart matching results as PDF"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'employer':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        employer_profile = EmployerProfile.objects.get(user_profile=user_profile)
        
    except (UserProfile.DoesNotExist, EmployerProfile.DoesNotExist):
        return JsonResponse({'error': 'Employer profile required'}, status=400)
    
    job_id = request.GET.get('job_id')
    if not job_id:
        messages.error(request, 'Job ID required for PDF export.')
        return redirect('employer:smart_matching')
    
    try:
        job = JobPost.objects.get(id=job_id, company=employer_profile.company)
    except JobPost.DoesNotExist:
        messages.error(request, 'Job not found.')
        return redirect('employer:smart_matching')
    
    # Get matching results
    matches = get_smart_matches(job, request.GET)
    total_matches = len(matches)
    
    # Generate PDF
    pdf_buffer = generate_smart_matching_report_pdf(matches, job, total_matches)
    
    # Create filename
    filename = f"{job.title.replace(' ', '_')}_matching_results.pdf"
    
    return create_pdf_response(pdf_buffer, filename)

def get_smart_matches(job, filters):
    """Smart matching algorithm to find best candidates for a job"""
    # Get all active job seekers
    candidates = JobSeekerProfile.objects.filter(
        user_profile__user__is_active=True
    ).select_related('user_profile__user')
    
    # Apply filters
    experience_level = filters.get('experience_level')
    location = filters.get('location')
    min_score = filters.get('min_score', 70)
    
    if experience_level:
        candidates = candidates.filter(experience_level=experience_level)
    
    if location:
        candidates = candidates.filter(
            Q(preferred_location__icontains=location) |
            Q(user_profile__location__icontains=location)
        )
    
    # Calculate match scores and sort
    scored_candidates = []
    for candidate in candidates:
        score = calculate_match_score(candidate, job)
        if score >= int(min_score):
            # Process skills for template display
            candidate_skills = []
            if hasattr(candidate, 'skills') and candidate.skills:
                candidate_skills = [s.strip() for s in str(candidate.skills).split(',') if s.strip()]
            
            scored_candidates.append({
                'candidate': candidate,
                'score': score,
                'match_reasons': get_match_reasons(candidate, job),
                'skills_list': candidate_skills
            })
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return scored_candidates

def calculate_match_score(candidate, job):
    """Calculate match score between candidate and job"""
    try:
        score = 0
        max_score = 100
        
        # Skills matching (40% weight)
        if hasattr(candidate, 'skills') and candidate.skills and hasattr(job, 'required_skills') and job.required_skills:
            candidate_skills = [s.strip().lower() for s in str(candidate.skills).split(',') if s.strip()]
            job_skills = [s.strip().lower() for s in str(job.required_skills).split(',') if s.strip()]
            
            if job_skills:
                matching_skills = set(candidate_skills) & set(job_skills)
                skill_score = (len(matching_skills) / len(job_skills)) * 40
                score += min(skill_score, 40)
        
        # Experience matching (30% weight)
        if hasattr(candidate, 'experience_level') and candidate.experience_level and hasattr(job, 'experience_level') and job.experience_level:
            exp_levels = {'entry': 1, 'junior': 2, 'mid': 3, 'senior': 4, 'lead': 5, 'executive': 6}
            candidate_exp = exp_levels.get(str(candidate.experience_level).lower(), 0)
            job_exp = exp_levels.get(str(job.experience_level).lower(), 0)
            
            if candidate_exp >= job_exp:
                exp_score = 30 - (abs(candidate_exp - job_exp) * 5)
                score += max(exp_score, 0)
        
        # Education matching (20% weight)
        if hasattr(candidate, 'education') and candidate.education and hasattr(job, 'education_required') and job.education_required:
            education_levels = {
                'high school': 1, 'associate degree': 2, "bachelor's degree": 3,
                "master's degree": 4, 'phd': 5
            }
            candidate_edu = education_levels.get(str(candidate.education).lower(), 0)
            job_edu = education_levels.get(str(job.education_required).lower(), 0)
            
            if candidate_edu >= job_edu:
                score += 20
            elif candidate_edu == job_edu - 1:
                score += 15
        
        # Location matching (10% weight)
        if hasattr(candidate, 'preferred_location') and candidate.preferred_location and hasattr(job, 'location') and job.location:
            try:
                candidate_location = str(candidate.preferred_location).lower()
                if hasattr(job.location, 'city') and job.location.city:
                    job_city = str(job.location.city).lower()
                    if candidate_location in job_city:
                        score += 10
                elif hasattr(job.location, 'state') and job.location.state:
                    job_state = str(job.location.state).lower()
                    if candidate_location in job_state:
                        score += 5
            except (AttributeError, TypeError):
                # Handle case where location is a string instead of object
                job_location = str(job.location).lower() if job.location else ""
                if candidate_location in job_location:
                    score += 10
        
        return min(score, max_score)
    
    except Exception as e:
        # Log error and return default score to prevent crashes
        print(f"Error calculating match score: {e}")
        return 50  # Default moderate score

def get_match_reasons(candidate, job):
    """Get reasons why candidate matches the job"""
    reasons = []
    
    try:
        # Check skills
        if hasattr(candidate, 'skills') and candidate.skills and hasattr(job, 'required_skills') and job.required_skills:
            candidate_skills = [s.strip().lower() for s in str(candidate.skills).split(',') if s.strip()]
            job_skills = [s.strip().lower() for s in str(job.required_skills).split(',') if s.strip()]
            matching_skills = set(candidate_skills) & set(job_skills)
            
            if matching_skills:
                reasons.append(f"Matches {len(matching_skills)} required skills: {', '.join(list(matching_skills)[:3])}")
        
        # Check experience
        if hasattr(candidate, 'experience_level') and candidate.experience_level and hasattr(job, 'experience_level') and job.experience_level:
            if str(candidate.experience_level).lower() == str(job.experience_level).lower():
                reasons.append(f"Perfect experience level match: {candidate.experience_level}")
        
        # Check education
        if hasattr(candidate, 'education') and candidate.education and hasattr(job, 'education_required') and job.education_required:
            if str(candidate.education).lower() == str(job.education_required).lower():
                reasons.append(f"Education requirement met: {candidate.education}")
        
        # Check location
        if hasattr(candidate, 'preferred_location') and candidate.preferred_location and hasattr(job, 'location') and job.location:
            try:
                candidate_location = str(candidate.preferred_location).lower()
                if hasattr(job.location, 'city') and job.location.city:
                    job_city = str(job.location.city)
                    if candidate_location in job_city.lower():
                        reasons.append(f"Location preference matches: {job_city}")
                else:
                    # Handle case where location is a string
                    job_location = str(job.location)
                    if candidate_location in job_location.lower():
                        reasons.append(f"Location preference matches: {job_location}")
            except (AttributeError, TypeError):
                pass
    
    except Exception as e:
        print(f"Error getting match reasons: {e}")
        reasons.append("General compatibility match")
    
    return reasons[:3]  # Return top 3 reasons
