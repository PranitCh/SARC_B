from decimal import Decimal
from django import forms
from .models import SplitGroup, get_friends
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class CreateGroupForm(forms.Form):
    name = forms.CharField(
        max_length=64,
        widget=forms.TextInput(
            attrs={
                "class": "form-control rounded-pill",
                "placeholder": "e.g. Goa trip, Flatmates, Office lunch",
            }
        ),
    )
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        super(CreateGroupForm, self).__init__(*args, **kwargs)
        friends = get_friends(user)
        self.fields["members"].queryset = friends.exclude(pk=user.pk)

class SettleForm(forms.Form):
    from_user = forms.IntegerField()
    to_user = forms.IntegerField()
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group

    def clean(self):
        cleaned = super().clean()

        from_id = cleaned.get("from_user")
        to_id = cleaned.get("to_user")
        amount = cleaned.get("amount")

        if not from_id or not to_id or not amount:
            return cleaned
        
        if from_id == to_id:
            raise forms.ValidationError("Invalid settlement users.")
        
        from_user = User.objects.filter(
            id=from_id,
            split_memberships__group=self.group,
        ).first()

        to_user = User.objects.filter(
            id=to_id,
            split_memberships__group=self.group,
        ).first()

        if not from_user or not to_user:
            raise forms.ValidationError("Users must belong to the group.")

        cleaned["from_user"] = from_user
        cleaned["to_user"] = to_user

        return cleaned