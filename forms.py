from django import forms

from core import models as core_models


class FileChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.__str__()} (Label: {obj.label}, last modified: {obj.last_modified.strftime('%Y-%m-%d %H:%M')})"


class FileSelectionForm(forms.Form):
    file = FileChoiceField(
        queryset=core_models.File.objects.none(),
        widget=forms.RadioSelect,
        label='File to Convert'
    )

    def __init__(self, *args, **kwargs):
        files = kwargs.pop('files')
        super(FileSelectionForm, self).__init__(*args, **kwargs)
        self.fields['file'].queryset = files

