from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Select a file')


class SitemapForm(forms.Form):
    sitemap_urls = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter one or more sitemap URLs, each on a new line'}),
        label='Sitemap URLs',
        help_text='Enter one or more sitemap URLs, each on a new line.'
    )