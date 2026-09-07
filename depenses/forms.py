from django import forms
from .models import Depense
from django.utils import timezone

class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['type_depense', 'quartier', 'prix', 'lieu', 'date', 'commentaire', 'photo']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'commentaire': forms.Textarea(attrs={'rows': 3}),
            'prix': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }
    
    def clean_date(self):
        date = self.cleaned_data['date']
        if date > timezone.now().date():
            raise forms.ValidationError("La date ne peut pas être dans le futur.")
        return date
    
    def clean_prix(self):
        prix = self.cleaned_data['prix']
        if prix <= 0:
            raise forms.ValidationError("Le prix doit être supérieur à 0.")
        return prix