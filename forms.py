from django import forms

from core import models as core_models


class FileChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.__str__()} (Label: {obj.label}, last modified: {obj.last_modified.strftime('%Y-%m-%d %H:%M')})"


CONVERSION_EXTENSIONS = ('.zip', '.docx', '.doc', '.odt', '.rtf', '.pdf')
CONVERSION_MAX_UPLOAD = 100 * 1024 * 1024


class ConversionUploadForm(forms.Form):
    file = forms.FileField(
        label='File to convert',
        help_text='A zipped LaTeX project, or a DOCX, DOC, ODT, RTF or PDF file. Maximum 100 MB.',
    )

    def clean_file(self):
        upload = self.cleaned_data['file']
        if not upload.name.lower().endswith(CONVERSION_EXTENSIONS):
            raise forms.ValidationError(
                'Upload a .zip, .docx, .doc, .odt, .rtf or .pdf file.'
            )
        if upload.size > CONVERSION_MAX_UPLOAD:
            raise forms.ValidationError('The file is larger than 100 MB.')
        return upload


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

