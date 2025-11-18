from django import forms
from .models import Order
from .shipping import method_choices

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'address',
            'postal_code', 'city', 'phone',
            'shipping_method', 'payment_method'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Postal'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'shipping_method': forms.RadioSelect(),
            'payment_method': forms.RadioSelect(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].required = False
        self.fields['postal_code'].required = False
        self.fields['city'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        shipping_method = cleaned_data.get('shipping_method')
        address = cleaned_data.get('address')
        city = cleaned_data.get('city')
        postal_code = cleaned_data.get('postal_code')
        
        # If delivery method, require address fields
        if shipping_method == 'home':
            if not address or not city or not postal_code:
                raise forms.ValidationError(
                    'La dirección, ciudad y código postal son requeridos para envío a domicilio.'
                )
        
        return cleaned_data


