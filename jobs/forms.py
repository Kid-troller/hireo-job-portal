from django import forms
from .models import JobPost, JobCategory, JobLocation, JobAlert
from accounts.models import JobSeekerProfile

class JobPostForm(forms.ModelForm):
    STATUS_CHOICES = [
        ('draft', 'Save as Draft'),
        ('active', 'Publish Immediately'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='active',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Choose whether to save as draft or publish immediately'
    )
    
    class Meta:
        model = JobPost
        fields = [
            'title', 'category', 'location', 'description', 'requirements',
            'responsibilities', 'benefits', 'employment_type', 'experience_level',
            'min_experience', 'max_experience', 'min_salary', 'max_salary',
            'salary_currency', 'is_salary_negotiable', 'is_salary_visible',
            'required_skills', 'preferred_skills', 'education_required',
            'application_deadline', 'is_remote', 'remote_percentage', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter job title'}),
            'description': forms.Textarea(attrs={'rows': 6, 'class': 'form-control', 'placeholder': 'Describe the job position, company culture, and what makes this role exciting'}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'List the required qualifications, experience, and skills'}),
            'responsibilities': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Outline the main duties and responsibilities'}),
            'benefits': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Describe benefits, perks, and compensation package'}),
            'required_skills': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter required skills separated by commas (e.g., Python, Django, JavaScript)'}),
            'preferred_skills': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter preferred skills separated by commas (optional)'}),
            'application_deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'min_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum salary', 'min': 0}),
            'max_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum salary', 'min': 0}),
            'salary_currency': forms.Select(attrs={'class': 'form-select'}),
            'remote_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'placeholder': '0-100'}),
            'min_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Years'}),
            'max_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Years'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'experience_level': forms.Select(attrs={'class': 'form-select'}),
            'education_required': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bachelor\'s degree in Computer Science'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields more explicit
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['requirements'].required = True
        self.fields['responsibilities'].required = True
        self.fields['category'].required = True
        self.fields['location'].required = True
        self.fields['employment_type'].required = True
        self.fields['experience_level'].required = True
        self.fields['application_deadline'].required = True
        
        # Add error messages for required fields
        self.fields['title'].error_messages = {
            'required': 'Job title is required and cannot be empty.',
            'max_length': 'Job title must be less than 200 characters.'
        }
        self.fields['description'].error_messages = {
            'required': 'Job description is required. Please provide a detailed description of the position.'
        }
        self.fields['requirements'].error_messages = {
            'required': 'Job requirements are required. Please specify the qualifications needed for this position.'
        }
        self.fields['responsibilities'].error_messages = {
            'required': 'Job responsibilities are required. Please outline the main duties for this role.'
        }
        self.fields['category'].error_messages = {
            'required': 'Please select a job category.',
            'invalid_choice': 'Please select a valid job category from the list.'
        }
        self.fields['location'].error_messages = {
            'required': 'Please select a job location.',
            'invalid_choice': 'Please select a valid location from the list.'
        }
        self.fields['employment_type'].error_messages = {
            'required': 'Please select an employment type (Full-time, Part-time, etc.).'
        }
        self.fields['experience_level'].error_messages = {
            'required': 'Please select the required experience level for this position.'
        }
        self.fields['application_deadline'].error_messages = {
            'required': 'Application deadline is required. Please set a date when applications will close.',
            'invalid': 'Please enter a valid date in the format YYYY-MM-DD.'
        }
        self.fields['min_salary'].error_messages = {
            'invalid': 'Minimum salary must be a valid number.',
            'min_value': 'Minimum salary cannot be negative.'
        }
        self.fields['max_salary'].error_messages = {
            'invalid': 'Maximum salary must be a valid number.',
            'min_value': 'Maximum salary cannot be negative.'
        }
        self.fields['remote_percentage'].error_messages = {
            'invalid': 'Remote percentage must be a number between 0 and 100.',
            'min_value': 'Remote percentage cannot be less than 0.',
            'max_value': 'Remote percentage cannot be more than 100.'
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 3:
                raise forms.ValidationError('Job title must be at least 3 characters long.')
            if len(title) > 200:
                raise forms.ValidationError('Job title must be less than 200 characters.')
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            description = description.strip()
            if len(description) < 50:
                raise forms.ValidationError('Job description must be at least 50 characters long to provide adequate information.')
        return description
    
    def clean_requirements(self):
        requirements = self.cleaned_data.get('requirements')
        if requirements:
            requirements = requirements.strip()
            if len(requirements) < 20:
                raise forms.ValidationError('Job requirements must be at least 20 characters long.')
        return requirements
    
    def clean_responsibilities(self):
        responsibilities = self.cleaned_data.get('responsibilities')
        if responsibilities:
            responsibilities = responsibilities.strip()
            if len(responsibilities) < 20:
                raise forms.ValidationError('Job responsibilities must be at least 20 characters long.')
        return responsibilities
    
    def clean_application_deadline(self):
        from datetime import date
        deadline = self.cleaned_data.get('application_deadline')
        if deadline:
            if deadline <= date.today():
                raise forms.ValidationError('Application deadline must be a future date.')
        return deadline
    
    def clean_min_salary(self):
        min_salary = self.cleaned_data.get('min_salary')
        if min_salary is not None:
            if min_salary < 0:
                raise forms.ValidationError('Minimum salary cannot be negative.')
            if min_salary > 10000000:  # 10 million limit
                raise forms.ValidationError('Minimum salary seems unreasonably high. Please check the amount.')
        return min_salary
    
    def clean_max_salary(self):
        max_salary = self.cleaned_data.get('max_salary')
        if max_salary is not None:
            if max_salary < 0:
                raise forms.ValidationError('Maximum salary cannot be negative.')
            if max_salary > 10000000:  # 10 million limit
                raise forms.ValidationError('Maximum salary seems unreasonably high. Please check the amount.')
        return max_salary
    
    def clean(self):
        cleaned_data = super().clean()
        min_salary = cleaned_data.get('min_salary')
        max_salary = cleaned_data.get('max_salary')
        min_experience = cleaned_data.get('min_experience')
        max_experience = cleaned_data.get('max_experience')
        
        # Salary validation
        if min_salary and max_salary:
            if min_salary > max_salary:
                raise forms.ValidationError({
                    'max_salary': 'Maximum salary must be greater than or equal to minimum salary.'
                })
        
        # Experience validation
        if min_experience is not None and max_experience is not None:
            if min_experience > max_experience:
                raise forms.ValidationError({
                    'max_experience': 'Maximum experience must be greater than or equal to minimum experience.'
                })
        
        # Check if at least one salary field is provided when the other is provided
        if (min_salary is not None or max_salary is not None):
            if min_salary is None and max_salary is not None:
                cleaned_data['min_salary'] = 0  # Set default minimum
            elif max_salary is None and min_salary is not None:
                # This is acceptable - just minimum salary specified
                pass
        
        return cleaned_data

class JobSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job title, keywords, or company'
        })
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, state, or remote'
        })
    )
    category = forms.ModelChoiceField(
        queryset=JobCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    employment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(JobPost.EMPLOYMENT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    experience_level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(JobPost.EXPERIENCE_LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_salary = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Salary'})
    )
    max_salary = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Salary'})
    )
    is_remote = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    # Advanced filters
    required_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Required skills (comma separated)'
        })
    )
    education_required = forms.ChoiceField(
        choices=[
            ('', 'Any Education'),
            ('high_school', 'High School'),
            ('associate', 'Associate Degree'),
            ('bachelor', 'Bachelor\'s Degree'),
            ('master', 'Master\'s Degree'),
            ('phd', 'PhD/Doctorate'),
            ('certification', 'Professional Certification')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_posted = forms.ChoiceField(
        choices=[
            ('', 'Any Time'),
            ('1', 'Last 24 Hours'),
            ('7', 'Last 7 Days'),
            ('30', 'Last 30 Days'),
            ('90', 'Last 3 Months')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    company_size = forms.ChoiceField(
        choices=[
            ('', 'Any Size'),
            ('small', 'Small (1-50 employees)'),
            ('medium', 'Medium (51-200 employees)'),
            ('large', 'Large (201-1000 employees)'),
            ('enterprise', 'Enterprise (1000+ employees)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    remote_percentage = forms.ChoiceField(
        choices=[
            ('', 'Any Remote Percentage'),
            ('0', 'On-site Only (0%)'),
            ('1-25', 'Hybrid (1-25%)'),
            ('26-50', 'Hybrid (26-50%)'),
            ('51-75', 'Mostly Remote (51-75%)'),
            ('76-99', 'Mostly Remote (76-99%)'),
            ('100', 'Fully Remote (100%)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('date_posted', 'Date Posted'),
            ('salary_high', 'Salary (High to Low)'),
            ('salary_low', 'Salary (Low to High)'),
            ('experience_level', 'Experience Level'),
            ('company_rating', 'Company Rating')
        ],
        required=False,
        initial='relevance',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class JobAlertForm(forms.ModelForm):
    class Meta:
        model = JobAlert
        fields = [
            'title', 'keywords', 'location', 'category', 'employment_type',
            'experience_level', 'min_salary', 'max_salary', 'is_remote', 'frequency'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alert name'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job keywords separated by commas'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'experience_level': forms.Select(attrs={'class': 'form-control'}),
            'min_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Salary'}),
            'max_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Salary'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = JobLocation.objects.filter(is_active=True)
        self.fields['category'].queryset = JobCategory.objects.filter(is_active=True)

class JobApplicationForm(forms.Form):
    cover_letter = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Write a compelling cover letter explaining why you are the perfect fit for this position...'
        })
    )
    resume = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Upload your resume (PDF, DOC, or DOCX)'
    )
    additional_files = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Upload additional documents if required (optional)'
    )
    
    def clean_cover_letter(self):
        cover_letter = self.cleaned_data.get('cover_letter')
        if cover_letter:
            cover_letter = cover_letter.strip()
            if len(cover_letter) < 50:
                raise forms.ValidationError('Cover letter must be at least 50 characters long to provide adequate information.')
            if len(cover_letter) > 5000:
                raise forms.ValidationError('Cover letter must be less than 5000 characters.')
        return cover_letter
    
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            allowed_extensions = ['pdf', 'doc', 'docx']
            file_extension = resume.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError('Please upload a valid resume file (PDF, DOC, or DOCX).')
            
            # Check file size (5MB limit)
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Resume file size must be less than 5MB.')
        
        return resume
    
    def clean_additional_files(self):
        additional_files = self.cleaned_data.get('additional_files')
        if additional_files:
            allowed_extensions = ['pdf', 'doc', 'docx', 'txt']
            file_extension = additional_files.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError('Additional files must be in PDF, DOC, DOCX, or TXT format.')
            
            # Check file size (5MB limit)
            if additional_files.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Additional files cannot exceed 5MB.')
        
        return additional_files

class JobCategoryForm(forms.ModelForm):
    class Meta:
        model = JobCategory
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FontAwesome icon class (e.g., fa-code)'}),
        }

class JobLocationForm(forms.ModelForm):
    class Meta:
        model = JobLocation
        fields = ['city', 'state', 'country', 'is_active']
        widgets = {
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AdvancedJobSearchForm(forms.Form):
    # Basic search
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job title, keywords, or company'
        })
    )
    
    # Location
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, state, or remote'
        })
    )
    
    # Multiple categories
    categories = forms.ModelMultipleChoiceField(
        queryset=JobCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    # Employment types
    employment_types = forms.MultipleChoiceField(
        choices=JobPost.EMPLOYMENT_TYPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    # Experience levels
    experience_levels = forms.MultipleChoiceField(
        choices=JobPost.EXPERIENCE_LEVEL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    # Salary range
    salary_range = forms.ChoiceField(
        choices=[
            ('', 'Any Salary'),
            ('0-30000', 'Under $30,000'),
            ('30000-50000', '$30,000 - $50,000'),
            ('50000-75000', '$50,000 - $75,000'),
            ('75000-100000', '$75,000 - $100,000'),
            ('100000-150000', '$100,000 - $150,000'),
            ('150000+', 'Over $150,000'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Remote work
    remote_options = forms.ChoiceField(
        choices=[
            ('', 'Any Work Type'),
            ('remote', 'Remote Only'),
            ('hybrid', 'Hybrid'),
            ('on_site', 'On-Site Only'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Date posted
    date_posted = forms.ChoiceField(
        choices=[
            ('', 'Any Time'),
            ('1', 'Last 24 hours'),
            ('3', 'Last 3 days'),
            ('7', 'Last week'),
            ('30', 'Last month'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Sort options
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Best Match'),
            ('date_posted', 'Most Recent'),
            ('salary_high', 'Highest Salary'),
            ('salary_low', 'Lowest Salary'),
            ('experience_level', 'Experience Level'),
            ('company_rating', 'Company Rating'),
        ],
        required=False,
        initial='relevance',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
