from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class SharingForm(forms.ModelForm):
    """The Public/Private switch for a user's library."""

    class Meta:
        model = User
        fields = ("library_is_public",)
        labels = {"library_is_public": "Make my library Public"}
        widgets = {"library_is_public": forms.CheckboxInput(attrs={"class": "toggle"})}
