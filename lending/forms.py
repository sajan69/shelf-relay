from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Item


def clean_components(raw):
    parts = [p.strip() for p in raw.splitlines() if p.strip()]
    if not 1 <= len(parts) <= 20 or any(len(p) > 60 for p in parts):
        raise forms.ValidationError(
            "Enter 1–20 components, at most 60 characters each."
        )
    if len(set(parts)) != len(parts):
        raise forms.ValidationError("Each component must have a different name.")
    return parts


class ItemForm(forms.ModelForm):
    checklist = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        max_length=1220,
        help_text="One component per line; include the main item.",
    )

    class Meta:
        model = Item
        fields = ["code", "name"]

    def clean_checklist(self):
        return clean_components(self.cleaned_data["checklist"])


class ReserveForm(forms.Form):
    borrower = forms.CharField(
        max_length=80,
        label="Borrower display name",
        help_text="Use the minimum label needed. No ID numbers or contact details.",
    )
    start = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    end = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Due back",
    )

    def clean(self):
        data = super().clean()
        start, end = data.get("start"), data.get("end")
        if start and end:
            if not start < end <= start + timedelta(days=30):
                raise forms.ValidationError(
                    "Choose a positive reservation of at most 30 elapsed days."
                )
            if (
                not timezone.now() - timedelta(minutes=5)
                <= start
                <= timezone.now() + timedelta(days=365)
            ):
                raise forms.ValidationError(
                    "Start must be now or within the next year."
                )
        return data


class ReturnForm(forms.Form):
    returned = forms.MultipleChoiceField(
        required=False, widget=forms.CheckboxSelectMultiple, label="Components received"
    )

    def __init__(self, components, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["returned"].choices = [
            (str(i), label) for i, label in enumerate(components)
        ]


class ResolveForm(forms.Form):
    note = forms.CharField(
        min_length=3,
        max_length=300,
        label="What was recovered or resolved?",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
