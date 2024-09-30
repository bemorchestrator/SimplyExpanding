# billing/forms.py

from django import forms
from .models import Invoice, InvoiceItem
from django.forms import inlineformset_factory

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_number',
            'client',
            'client_address',
            'invoice_date',
            'due_date',
            'status',
            'currency',
            'notes'
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'client': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'client_address': forms.Textarea(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'status': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'currency': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'notes': forms.Textarea(attrs={'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        # Make 'status' and 'currency' optional
        self.fields['status'].required = False
        self.fields['currency'].required = False

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ('description', 'quantity', 'rate')
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Item Description'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'placeholder': 'Quantity'
            }),
            'rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Item Price'
            }),
        }

# Create an inline formset for handling Invoice Items
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    fields=('description', 'quantity', 'rate'),
    extra=1,
    can_delete=True,
)
