from django import forms
from django.core.exceptions import ValidationError
from .models import ContactMessage, Propiedad


# ----------------------------
# Contact form
# ----------------------------
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["nombre", "email", "telefono", "mensaje"]
        widgets = {
            "mensaje": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Your message",
                "rows": 4
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Bootstrap classes & placeholders
        self.fields['nombre'].widget.attrs.update({"class": "form-control", "placeholder": "Your name"})
        self.fields['email'].widget.attrs.update({"class": "form-control", "placeholder": "Your email"})
        self.fields['telefono'].widget.attrs.update({"class": "form-control", "placeholder": "Your phone"})
        self.fields['mensaje'].widget.attrs.update({"class": "form-control", "placeholder": "Write your message here", "rows": 4})

        # Prefill for authenticated users
        if user and user.is_authenticated:
            self.fields['nombre'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            # read-only prefilled fields
            self.fields['nombre'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True


# ----------------------------
# Property form (+ multi-file uploads handled in the view)
# ----------------------------

# --- NEW: widget that supports multiple files ---
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class PropiedadForm(forms.ModelForm):
    # Optional field to upload multiple files; processed ONLY if form is valid (in the view)
    multimedia_files = forms.FileField(
        required=False,
        help_text="Upload files. They are processed only if the property data is valid.",
        widget=MultipleFileInput(attrs={"multiple": True})
    )

    class Meta:
        model = Propiedad
        fields = [
            "title", "description", "price_cop", "admin_fee_cop",
            "area_m2", "area_privada_m2", "rooms", "bathrooms", "parking_spaces",
            "location", "property_type", "estrato", "floor",
            "pets_allowed", "furnished", "amenities",
        ]
        # Opcional: puedes añadir widgets/attrs aquí si quieres estilizar inputs

    def clean(self):
        cleaned = super().clean()
        required = ["title", "description", "price_cop", "area_m2", "location"]
        errors = {}

        # Requireds
        for field in required:
            value = cleaned.get(field)
            if value in (None, ""):
                errors[field] = ValidationError("This field is required.")

        # Basic numeric validations
        price = cleaned.get("price_cop")
        area = cleaned.get("area_m2")

        if price is not None:
            try:
                if float(price) <= 0:
                    errors["price_cop"] = ValidationError("The total price must be greater than 0.")
            except Exception:
                errors["price_cop"] = ValidationError("Invalid price.")

        if area is not None:
            try:
                if float(area) <= 0:
                    errors["area_m2"] = ValidationError("The area must be greater than 0.")
            except Exception:
                errors["area_m2"] = ValidationError("Invalid area.")

        # price per m² (only if both are valid)
        if ("price_cop" not in errors) and ("area_m2" not in errors) and price is not None and area not in (None, 0):
            try:
                precio_m2 = float(price) / float(area)
                if precio_m2 <= 0:
                    errors["area_m2"] = ValidationError("The price per m² must be greater than 0.")
            except Exception:
                # ignore; already handled by individual field validations
                pass

        if errors:
            raise ValidationError(errors)

        # mark the form as ready for multimedia processing (handled in the view)
        self.enable_multimedia = True
        return cleaned

    def can_enable_multimedia(self) -> bool:
        return getattr(self, "enable_multimedia", False)

    def save(self, commit=True):
        # Media files are handled in the view after the instance is saved successfully.
        return super().save(commit=commit)
