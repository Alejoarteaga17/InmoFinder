from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from matplotlib.pylab import save
from .models import ContactMessage

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Nombre de usuario"})
        self.fields["password1"].widget.attrs.update({"class": "form-control", "placeholder": "Contraseña"})
        self.fields["password2"].widget.attrs.update({"class": "form-control", "placeholder": "Repite la contraseña"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "Correo electrónico"})

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Usuario"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Contraseña"})

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

            self.fields['nombre'].widget.attrs.update({"class": "form-control", "placeholder": "Tu nombre"})
            self.fields['email'].widget.attrs.update({"class": "form-control", "placeholder": "Tu correo electrónico"})
            self.fields['mensaje'].widget.attrs.update({"class": "form-control", "placeholder": "Tu mensaje", "rows": 4})
