from django import forms
from django.core.exceptions import ValidationError
from .models import ContactMessage, Propiedad


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        # ContactMessage uses spanish field names in the model
        fields = ["nombre", "email", "telefono", "mensaje"]
        widgets = {
            "mensaje": forms.Textarea(attrs={"class": "form-control", "placeholder": "Your Message", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # set bootstrap classes & placeholders
        self.fields['nombre'].widget.attrs.update({"class": "form-control", "placeholder": "Your name"})
        self.fields['email'].widget.attrs.update({"class": "form-control", "placeholder": "Your Email"})
        self.fields['mensaje'].widget.attrs.update({"class": "form-control", "placeholder": "Write your message here", "rows": 4})

        if user and user.is_authenticated:
            self.fields['nombre'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            # make name and email readonly for authenticated users
            self.fields['nombre'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True


class PropiedadForm(forms.ModelForm):
    # campo opcional para subir múltiples archivos desde el mismo form
    multimedia_files = forms.FileField(
        required=False,
        help_text="Upload files. They are processed only if the property data is valid."
    )

    class Meta:
        model = Propiedad
        # Use the new model field names
        fields = [
            "title", "description", "price_cop", "admin_fee_cop",
            "area_m2", "area_privada_m2", "rooms", "bathrooms", "parking_spaces",
            "location", "property_type", "estrato", "floor",
            "pets_allowed", "furnished", "amenities"
        ]

    def clean(self):
        cleaned = super().clean()
        required = ["title", "description", "price_cop", "area_m2", "location"]
        errors = {}

        for field in required:
            value = cleaned.get(field)
            if value in (None, ""):
                errors[field] = ValidationError("This field is required.")

        # basic numeric validations (use new names)
        price = cleaned.get("price_cop")
        area = cleaned.get("area_m2")
        precio_m2 = None
        try:
            if price is not None and area not in (None, 0):
                precio_m2 = float(price) / float(area)
        except Exception:
            precio_m2 = None

        if price is not None and price <= 0:
            errors["price_cop"] = ValidationError("The total price must be greater than 0.")
        if precio_m2 is not None and precio_m2 <= 0:
            errors["area_m2"] = ValidationError("The price per m² must be greater than 0.")
        if area is not None and area <= 0:
            errors["area_m2"] = ValidationError("The area must be greater than 0.")

        if errors:
            raise ValidationError(errors)
        # mark the form as ready for multimedia processing
        self.enable_multimedia = True
        return cleaned

    def can_enable_multimedia(self) -> bool:
        return getattr(self, "enable_multimedia", False)

    def save(self, commit=True):
        # We don't handle multimedia files here (it's done in the view).
        instance = super().save(commit=commit)
        return instance