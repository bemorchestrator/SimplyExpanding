from django import forms

class PayPeriodForm(forms.Form):
    pay_period_start = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Pay Period Start'
    )
    pay_period_end = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Pay Period End'
    )
