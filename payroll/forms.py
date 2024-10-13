from django import forms
from payroll.models import PayrollRecord
from django import forms
from .models import PayrollRecord

class PayPeriodForm(forms.Form):
    pay_period_start = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control bg-gray-700 border border-gray-600 rounded-md py-2 px-3 text-white'
        }),
        label='Pay Period Start'
    )
    pay_period_end = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control bg-gray-700 border border-gray-600 rounded-md py-2 px-3 text-white'
        }),
        label='Pay Period End'
    )




class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            'pay_period_start',
            'pay_period_end',
            'total_income',
            'bonus',
            'deductions',
            'absence_deductions',
            'other_deductions',
            'average_daily_pay',
            'remarks',
        ]
        widgets = {
            'pay_period_start': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'pay_period_end': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'total_income': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'bonus': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'deductions': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'absence_deductions': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'other_deductions': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'average_daily_pay': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
            'remarks': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full p-2 border border-gray-700 rounded bg-gray-700 text-white'
            }),
        }

    
class ProcessPayrollForm(forms.Form):
        referral_code = forms.CharField(
            max_length=100, 
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'bg-gray-700 border border-gray-600 rounded-md py-2 px-3 w-full text-white',
                'placeholder': 'Enter referral code'
            })
        )
    
        PAYMENT_PLATFORM_CHOICES = [
            ('gcash', 'GCash'),
            ('bank_transfer', 'Bank Transfer'),
            ('maya', 'Maya'),
            ('other', 'Other'),
        ]
        
        payment_platform = forms.ChoiceField(
            choices=PAYMENT_PLATFORM_CHOICES,
            required=True,
            widget=forms.Select(attrs={
                'class': 'bg-gray-700 border border-gray-600 rounded-md py-2 px-3 w-full text-white'
            })
        )
        
        other_payment_platform = forms.CharField(
            max_length=100, 
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'bg-gray-700 border border-gray-600 rounded-md py-2 px-3 w-full text-white',
                'placeholder': 'Specify other payment platform'
            })
        )
        
        payment_proof = forms.ImageField(
            required=False,
            widget=forms.ClearableFileInput(attrs={
                'class': 'bg-gray-700 border border-gray-600 rounded-md py-2 px-3 w-full text-white'
            })
        )