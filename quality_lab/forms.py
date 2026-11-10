from django import forms

from .models import EvaluacionExperiencia


class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = EvaluacionExperiencia
        fields = ["version", "participante", "facilidad_seleccion", "comprension_horarios",
                  "informacion_suficiente", "mejoras"]
        widgets = {
            "version": forms.RadioSelect,
            "facilidad_seleccion": forms.RadioSelect,
            "comprension_horarios": forms.RadioSelect,
            "informacion_suficiente": forms.RadioSelect,
            "participante": forms.TextInput(attrs={"class": "input", "maxlength": 80}),
            "mejoras": forms.Textarea(attrs={"class": "input", "rows": 4, "maxlength": 1500}),
        }
