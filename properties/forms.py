from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from matplotlib.pylab import save
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["nombre", "email", "mensaje"]
        widgets = {
            "mensaje": forms.Textarea(attrs={"class": "form-control", "placeholder": "Your Message", "rows": 4}),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            self.fields['nombre'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            self.fields['nombre'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True

            self.fields['nombre'].widget.attrs.update({"class": "form-control", "placeholder": "Your name"})
            self.fields['email'].widget.attrs.update({"class": "form-control", "placeholder": "Your Email"})
            self.fields['mensaje'].widget.attrs.update({"class": "form-control", "placeholder": "Write your message here", "rows": 4})
