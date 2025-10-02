from django import forms
from django.core.exceptions import ValidationError
from .models import ContactMessage, Propiedad

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "placeholder": "Your Message", "rows": 4}),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            self.fields['name'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True

            self.fields['name'].widget.attrs.update({"class": "form-control", "placeholder": "Your name"})
            self.fields['email'].widget.attrs.update({"class": "form-control", "placeholder": "Your Email"})
            self.fields['message'].widget.attrs.update({"class": "form-control", "placeholder": "Write your message here", "rows": 4})

class PropiedadForm(forms.ModelForm):
    # campo opcional para subir múltiples archivos desde el mismo form
    multimedia_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
        help_text="Upload files. They are processed only if the property data is valid."
    )

    class Meta:
        model = Propiedad
        fields = [
            "nombre", "descripcion", "precio_total", "precio_m2",
            "habitaciones", "banos", "parqueaderos", "area",
            "ubicacion", "tipo", "zonas_comunes", "fecha_disponibilidad",
            "garaje", "mascotas", "estrato"
        ]
        widgets = {
            "fecha_disponibilidad": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        required = ["nombre", "descripcion", "precio_total", "area", "ubicacion"]
        errors = {}

        for field in required:
            value = cleaned.get(field)
            if value in (None, ""):
                errors[field] = ValidationError("This field is required.")

        # basic numeric validations
        precio_total = cleaned.get("precio_total")
        area = cleaned.get("area")
        precio_m2 = (precio_total / area) if (precio_total is not None and area not in (None, 0)) else None

        if precio_total is not None and precio_total <= 0:
            errors["precio_total"] = ValidationError("The total price must be greater than 0.")
        if precio_m2 is not None and precio_m2 <= 0:
            errors["precio_m2"] = ValidationError("The price per m² must be greater than 0.")
        if area is not None and area <= 0:
            errors["area"] = ValidationError("The area must be greater than 0.")

        if errors:
            raise ValidationError(errors)

        # If we reached here, the property has all the necessary data
        self.enable_multimedia = True
        return cleaned

    def can_enable_multimedia(self) -> bool:
        return getattr(self, "enable_multimedia", False)

    def save(self, commit=True):
        # We don't handle multimedia files here (it's done in the view).
        instance = super().save(commit=commit)
        return instance