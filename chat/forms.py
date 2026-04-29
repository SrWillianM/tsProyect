from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import ChannelKind, Profile, Room


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("nickname", "avatar")
        widgets = {
            "nickname": forms.TextInput(attrs={"placeholder": "Tu apodo visible"}),
            "avatar": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_nickname(self):
        nickname = (self.cleaned_data.get("nickname") or "").strip()
        if not nickname:
            raise forms.ValidationError("El apodo es obligatorio.")
        return nickname[:50]


class RoomCreateForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("name", "kind")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Nuevo canal"}),
            "kind": forms.Select(),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("El nombre es obligatorio.")
        return name[:100]

    def clean_kind(self):
        kind = self.cleaned_data.get("kind") or ChannelKind.CHAT
        if kind not in ChannelKind.values:
            raise forms.ValidationError("Tipo de canal inválido.")
        return kind
