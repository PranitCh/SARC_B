from django import forms
from .models import Budget, Goal, Transaction, Subscription
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['name', 'amount']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter budget name',
                'class': 'form-control',
            }),
            'amount': forms.NumberInput(attrs={
                'placeholder': 'Amount',
                'class': 'form-control',
                'step': '0.01',
            }),
        }

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter goal name',
                'class': 'form-control'
            }),
            'target': forms.NumberInput(attrs={
                'placeholder': 'Target amount',
                'class': 'form-control',
                'step': '0.01'
            }),
        }

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['desc', 'amount', 'is_income']
        widgets = {
            'desc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Description'
                }),
            'amount': forms.NumberInput(attrs=
                {'class': 'form-control', 
                'step': '0.01',
                'placeholder': 'Enter amount' 
                }),
            'is_income': forms.CheckboxInput(attrs=
                {'class': 'form-check-input',
                }),
        }
    
    def save(self, commit=True, budget=None):
        instance = super().save(commit=False)
        if budget:
            instance.budget = budget
        if commit:
            instance.save()  # FORCE SAVE
            print(f"FORCED SAVE ID:{instance.id}")
        return instance

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class and inline styles
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'style': 'background-color: inherit !important; color: inherit !important;'
            })

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': ''
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': ''
        })
    )

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['name', 'amount', 'billing_day', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Amount'}),
            'billing_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 28, 'billing-day': 'Billing days'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }