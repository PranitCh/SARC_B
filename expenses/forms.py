from django import forms
from .models import Budget, Goal, Transaction

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['name', 'amount']

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['desc', 'amount', 'is_income']
        widgets = {
            'desc': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_income': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True, budget=None):
        instance = super().save(commit=False)
        if budget:
            instance.budget = budget
        if commit:
            instance.save()  # FORCE SAVE
            print(f"FORCED SAVE ID:{instance.id}")
        return instance
