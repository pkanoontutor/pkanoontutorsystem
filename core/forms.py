# core/forms.py
from django import forms
from .models import Sheet

class SheetUpdateRowForm(forms.Form):
    class_subject_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    subject_name = forms.CharField(required=False)

    sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.filter(is_active=True).select_related("subject").order_by("subject__name", "code"),
        required=False,
        widget=forms.Select(attrs={
            "class": "sheet-select",
            "data-placeholder": "พิมพ์รหัส / ชื่อชีท",
        }),
    )

    page_taught_to = forms.IntegerField(required=False, min_value=0)
    question_taught_to = forms.IntegerField(required=False, min_value=0)
    last_teacher = forms.CharField(required=False)
