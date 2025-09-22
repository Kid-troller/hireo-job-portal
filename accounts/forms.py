from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, JobSeekerProfile, Education, Experience, Skill, Certification, SecurityQuestion, UserSecurityAnswer
from employers.models import Company, EmployerProfile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        required=True,
        label='Account Type'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

class JobSeekerProfileForm(forms.ModelForm):
    class Meta:
        model = JobSeekerProfile
        fields = [
            'resume', 'cover_letter', 'expected_salary', 'preferred_location',
            'availability', 'linkedin_url', 'github_url', 'portfolio_url',
            'skills', 'experience_years', 'education_level', 'certifications_text',
            'languages', 'is_available_for_work'
        ]
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 4}),
            'skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your skills separated by commas'}),
            'certifications_text': forms.Textarea(attrs={'rows': 3}),
            'languages': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter languages you speak'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'phone', 'address', 'city', 'state', 'country', 'zip_code',
            'profile_picture', 'bio', 'date_of_birth'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            'degree_type', 'institution', 'field_of_study', 'start_date',
            'end_date', 'is_current', 'gpa', 'description'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_current = cleaned_data.get('is_current')
        
        if not is_current and end_date and start_date and end_date <= start_date:
            raise forms.ValidationError('End date must be after start date.')
        
        return cleaned_data

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            'company_name', 'job_title', 'start_date', 'end_date',
            'is_current', 'description', 'responsibilities', 'achievements'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'responsibilities': forms.Textarea(attrs={'rows': 3}),
            'achievements': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_current = cleaned_data.get('is_current')
        
        if not is_current and end_date and start_date and end_date <= start_date:
            raise forms.ValidationError('End date must be after start date.')
        
        return cleaned_data

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'level', 'years_of_experience']

class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = [
            'name', 'issuing_organization', 'issue_date', 'expiry_date',
            'credential_id', 'credential_url'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'description', 'industry', 'company_size', 'founded_year',
            'website', 'logo', 'address', 'city', 'state', 'country', 'zip_code',
            'phone', 'email', 'linkedin_url', 'facebook_url', 'twitter_url',
            'company_culture', 'benefits'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'company_culture': forms.Textarea(attrs={'rows': 3}),
            'benefits': forms.Textarea(attrs={'rows': 3}),
        }

class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['position', 'department', 'is_primary_contact']

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autocomplete': 'username'
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        }),
        label='Password'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'autofocus': True})

class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('New passwords do not match.')
        
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
        queryset=None,
        required=False,
        empty_label="All Categories"
    )
    employment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('internship', 'Internship'),
            ('freelance', 'Freelance'),
            ('temporary', 'Temporary'),
        ],
        required=False
    )
    experience_level = forms.ChoiceField(
        choices=[('', 'All Levels')] + [
            ('entry', 'Entry Level'),
            ('junior', 'Junior'),
            ('mid', 'Mid Level'),
            ('senior', 'Senior'),
            ('lead', 'Lead'),
            ('executive', 'Executive'),
        ],
        required=False
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
    is_remote = forms.BooleanField(required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This will be set in the view
        self.fields['category'].queryset = None


# Forgot Password Forms using Security Questions
class ForgotPasswordRequestForm(forms.Form):
    """Form to request password reset using username/email"""
    username_or_email = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email address',
            'autocomplete': 'username'
        }),
        label='Username or Email'
    )
    
    def clean_username_or_email(self):
        username_or_email = self.cleaned_data.get('username_or_email')
        
        # Try to find user by username or email
        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise forms.ValidationError('No account found with this username or email.')
        
        # Check if user has security questions set up
        if not user.security_answers.exists():
            raise forms.ValidationError('This account does not have security questions set up. Please contact support.')
        
        return username_or_email


class SecurityQuestionsForm(forms.Form):
    """Form to answer security questions for password reset"""
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Get all security questions for this user
        security_answers = user.security_answers.select_related('security_question').all()
        
        for i, security_answer in enumerate(security_answers):
            field_name = f'answer_{security_answer.security_question.id}'
            self.fields[field_name] = forms.CharField(
                label=security_answer.security_question.question_text,
                max_length=200,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter your answer',
                    'autocomplete': 'off'
                }),
                required=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        correct_answers = 0
        
        # Check each answer
        security_answers = self.user.security_answers.select_related('security_question').all()
        
        for security_answer in security_answers:
            field_name = f'answer_{security_answer.security_question.id}'
            provided_answer = cleaned_data.get(field_name, '')
            
            if security_answer.check_answer(provided_answer):
                correct_answers += 1
        
        # Require at least one correct answer
        if correct_answers == 0:
            raise forms.ValidationError('None of your answers are correct. Please try again.')
        
        # Store the number of correct answers for the view
        self.correct_answers = correct_answers
        
        return cleaned_data


class NewPasswordForm(forms.Form):
    """Form to set new password after security question verification"""
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        }),
        min_length=8,
        help_text='Password must be at least 8 characters long.'
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('The two password fields must match.')
        
        return cleaned_data


class SecurityQuestionsSetupForm(forms.Form):
    """Form to set up security questions during registration or profile setup"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get active security questions
        questions = SecurityQuestion.objects.filter(is_active=True)
        
        for i, question in enumerate(questions[:3]):  # Limit to first 3 questions
            self.fields[f'question_{question.id}'] = forms.CharField(
                label=question.question_text,
                max_length=200,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter your answer',
                    'autocomplete': 'off'
                }),
                required=True,
                help_text='Your answer will be used for password recovery. Please remember it.'
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure all answers are provided and not empty
        for field_name, value in cleaned_data.items():
            if field_name.startswith('question_') and not value.strip():
                raise forms.ValidationError('All security questions must be answered.')
        
        return cleaned_data
