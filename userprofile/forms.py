from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Customer


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    address = forms.CharField(max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Customer.objects.create(
                user=user, username=user.username, first_name=user.first_name, last_name=user.last_name,
                email=user.email, phone=self.cleaned_data['phone'], address=self.cleaned_data['address'],
            )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'pix')
        labels = {'pix': 'Profile picture'}
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'street-address'}),
            'pix': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError('Another account already uses this email.')
        return email

    def clean_pix(self):
        pix = self.cleaned_data.get('pix')
        if pix and hasattr(pix, 'size') and pix.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Please choose an image under 2 MB.')
        return pix

    def save(self, commit=True):
        customer = super().save(commit=commit)
        if commit:  # keep the login account in step with the profile
            user = customer.user
            user.first_name, user.last_name, user.email = customer.first_name, customer.last_name, customer.email
            user.save(update_fields=['first_name', 'last_name', 'email'])
        return customer
