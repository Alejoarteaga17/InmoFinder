from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono"})
    )

    class Meta:
        model = Usuario   # 👉 Usamos tu modelo personalizado
        fields = ["username", "email", "phone", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Username"})
        self.fields["password1"].widget.attrs.update({"class": "form-control", "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": "form-control", "placeholder": "Repeat Password"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "Email"})
        self.fields["phone"].widget.attrs.update({"class": "form-control", "placeholder": "Phone (optional)"})

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("El teléfono debe contener solo números.")
            if len(phone) != 10:
                raise forms.ValidationError("El teléfono debe tener exactamente 10 dígitos.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        # 👤 Todos los nuevos usuarios son comprador por defecto
        user.is_comprador = True
        user.is_propietario = False

        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )


class UserUpdateForm(forms.ModelForm):
    """Formulario para editar información básica del usuario."""
    class Meta:
        model = Usuario
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Estilos Bootstrap
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
        self.fields["username"].widget.attrs.setdefault("placeholder", "Username")
        self.fields["email"].widget.attrs.setdefault("placeholder", "Email")
        self.fields["first_name"].widget.attrs.setdefault("placeholder", "First name")
        self.fields["last_name"].widget.attrs.setdefault("placeholder", "Last name")
        self.fields["phone"].widget.attrs.setdefault("placeholder", "Phone")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = Usuario.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email

        def clean_phone(self):
            phone = self.cleaned_data.get("phone", "")
            if phone:
                if not phone.isdigit():
                    raise forms.ValidationError("El teléfono debe contener solo números.")
                if len(phone) != 10:
                    raise forms.ValidationError("El teléfono debe tener exactamente 10 dígitos.")
            return phone