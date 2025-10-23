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
    # Este campo NO es parte del modelo, solo para subir archivos
    # El atributo 'multiple' lo agregamos en el template
    multimedia_files = forms.FileField(
        required=False,
        help_text="Selecciona uno o más archivos para subir.",
        widget=forms.FileInput(attrs={'class': 'form-control'})
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
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price_cop': forms.NumberInput(attrs={'class': 'form-control'}),
            'admin_fee_cop': forms.NumberInput(attrs={'class': 'form-control'}),
            'area_m2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'area_privada_m2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'parking_spaces': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'property_type': forms.Select(attrs={'class': 'form-control'}),
            'estrato': forms.NumberInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'pets_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'furnished': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter amenities as JSON, e.g., ["Pool", "Gym"]'}),
        }

    def clean(self):
        cleaned = super().clean()
        
        # Validar campos numéricos específicos
        price = cleaned.get("price_cop")
        area = cleaned.get("area_m2")

        # Validar que el precio sea positivo
        if price is not None and price <= 0:
            self.add_error("price_cop", "El precio total debe ser mayor que 0.")

        # Validar que el área sea positiva
        if area is not None and area <= 0:
            self.add_error("area_m2", "El área debe ser mayor que 0.")

        # Validar precio por m² solo si ambos valores existen
        if price and area and area > 0:
            precio_m2 = float(price) / float(area)
            if precio_m2 <= 0:
                self.add_error("area_m2", "El precio por m² debe ser mayor que 0.")

        # Solo habilitar multimedia si no hay errores
        if not self.errors:
            self.enable_multimedia = True
        
        return cleaned

    def can_enable_multimedia(self) -> bool:
        return getattr(self, "enable_multimedia", False)

    def save(self, commit=True):
        # We don't handle multimedia files here (it's done in the view).
        instance = super().save(commit=commit)
        return instance