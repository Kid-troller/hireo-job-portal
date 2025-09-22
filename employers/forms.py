from django import forms
from .models import Company, EmployerProfile, CompanyReview, CompanyPhoto, CompanyBenefit

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
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name', 'required': True}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Company description', 'required': True}),
            'industry': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'company_size': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'founded_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1800, 'max': 2024}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.company.com'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Company address', 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'required': True}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province', 'required': True}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country', 'required': True}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP/Postal Code', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@company.com', 'required': True}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'LinkedIn URL'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Facebook URL'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Twitter URL'}),
            'company_culture': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Describe your company culture'}),
            'benefits': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'List company benefits and perks'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional
        self.fields['founded_year'].required = False
        self.fields['website'].required = False
        self.fields['logo'].required = False
        self.fields['phone'].required = False
        self.fields['linkedin_url'].required = False
        self.fields['facebook_url'].required = False
        self.fields['twitter_url'].required = False
        self.fields['company_culture'].required = False
        self.fields['benefits'].required = False

class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['position', 'department', 'is_primary_contact']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your position/title', 'required': True}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'is_primary_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make department optional
        self.fields['department'].required = False

class CompanyReviewForm(forms.ModelForm):
    class Meta:
        model = CompanyReview
        fields = ['rating', 'title', 'review', 'pros', 'cons', 'is_anonymous']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review title'}),
            'review': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Share your experience working at this company'}),
            'pros': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'What are the best things about working here?'}),
            'cons': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'What could be improved?'}),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CompanyPhotoForm(forms.ModelForm):
    class Meta:
        model = CompanyPhoto
        fields = ['image', 'caption', 'is_featured']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Photo caption'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CompanyBenefitForm(forms.ModelForm):
    class Meta:
        model = CompanyBenefit
        fields = ['name', 'description', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Benefit name'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Describe this benefit'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FontAwesome icon class (e.g., fa-heart)'}),
        }
