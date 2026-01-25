# core/forms.py
from django import forms

from .models import Sheet


class SheetUpdateRowForm(forms.Form):
    """
    ฟอร์ม 1 แถว สำหรับหน้า Sheet Update
    """
    class_subject_id = forms.IntegerField(widget=forms.HiddenInput())
    subject_name = forms.CharField(required=False, widget=forms.HiddenInput())

    sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.all().order_by("code"),
        required=False,
        widget=forms.Select(attrs={
            "class": "sheet-select",  # ✅ ให้ Select2 จับได้
            "data-placeholder": "พิมพ์รหัส / ชื่อชีท",
        })
    )

    page_taught_to = forms.IntegerField(required=False, min_value=0)
    question_taught_to = forms.IntegerField(required=False, min_value=0)
    last_teacher = forms.CharField(required=False)
