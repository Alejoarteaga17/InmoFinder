from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from matplotlib.pylab import save
from .models import ContactMessage

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Username"})
        self.fields["password1"].widget.attrs.update({"class": "form-control", "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": "form-control", "placeholder": "Repeat Password"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "Email"})

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Username"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Password"})

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
