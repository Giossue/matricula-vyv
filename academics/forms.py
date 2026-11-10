from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Asignatura, Docente, Horario, PeriodoAcademico, Seccion


class FormularioBase(forms.ModelForm):
    """Agrega atributos HTML5 para que el navegador valide antes de enviar."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            clase = "select" if isinstance(widget, forms.Select) else "input"
            widget.attrs.setdefault("class", clase)
            if isinstance(campo, forms.IntegerField):
                if campo.min_value is not None:
                    widget.attrs["min"] = campo.min_value
                if campo.max_value is not None:
                    widget.attrs["max"] = campo.max_value


class AsignaturaForm(FormularioBase):
    class Meta:
        model = Asignatura
        fields = ["codigo", "nombre", "creditos", "carrera", "semestre_recomendado", "estado"]
        widgets = {"codigo": forms.TextInput(attrs={"pattern": "[A-Za-z0-9-]{3,12}", "title": "3 a 12 letras, números o guiones"})}

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class DocenteForm(FormularioBase):
    class Meta:
        model = Docente
        fields = ["nombre", "apellido", "correo", "activo"]
        widgets = {"activo": forms.CheckboxInput(attrs={"class": "checkbox"})}


class PeriodoForm(FormularioBase):
    class Meta:
        model = PeriodoAcademico
        fields = ["nombre", "fecha_inicio", "fecha_fin", "fecha_limite_matricula", "estado"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_limite_matricula": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class SeccionForm(FormularioBase):
    class Meta:
        model = Seccion
        fields = ["asignatura", "periodo", "paralelo", "docente", "capacidad_maxima"]
        widgets = {"paralelo": forms.TextInput(attrs={"maxlength": 5, "pattern": "[A-Za-z0-9]{1,5}"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo se ofrecen asignaturas activas y docentes activos (más los ya asignados al editar).
        self.fields["asignatura"].queryset = Asignatura.objects.filter(
            Q(estado=Asignatura.Estado.ACTIVA) | Q(pk=self.instance.asignatura_id)
        )
        self.fields["docente"].queryset = Docente.objects.filter(Q(activo=True) | Q(pk=self.instance.docente_id))

    def clean_paralelo(self):
        return self.cleaned_data["paralelo"].strip().upper()


class HorarioForm(FormularioBase):
    class Meta:
        model = Horario
        fields = ["dia_semana", "hora_inicio", "hora_fin"]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fin": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }


class HorarioFormSetBase(BaseInlineFormSet):
    def clean(self):
        super().clean()
        bloques = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            datos = form.cleaned_data
            if not all(datos.get(c) for c in ("dia_semana", "hora_inicio", "hora_fin")):
                continue
            nuevo = Horario(**{c: datos[c] for c in ("dia_semana", "hora_inicio", "hora_fin")})
            for previo in bloques:
                if nuevo.se_cruza_con(previo):
                    raise forms.ValidationError(f"Los bloques {previo} y {nuevo} de esta sección se superponen.")
            bloques.append(nuevo)
        if not bloques:
            raise forms.ValidationError("La sección necesita al menos un bloque de horario.")


HorarioFormSet = inlineformset_factory(
    Seccion, Horario, form=HorarioForm, formset=HorarioFormSetBase, extra=1, can_delete=True, max_num=6,
)
