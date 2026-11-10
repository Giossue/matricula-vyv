from django import forms
from django.contrib.auth.forms import AuthenticationForm


class IngresoForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        max_length=50,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username", "required": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "required": True}),
    )

    error_messages = {
        "invalid_login": "Usuario o contraseña incorrectos. Revisa los datos e inténtalo de nuevo.",
        "inactive": "Esta cuenta está desactivada.",
    }
