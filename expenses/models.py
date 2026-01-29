from django.db import models  
from django.contrib.auth.models import User
from django.utils import timezone  # for timestamps maybe
import datetime  # unused lol

# Budget model - no slug
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)  # auto timestamp
    
    def __str__(self):
        return f"{self.name} - ${self.amount}"

# goals for saving up stuff
class Goal(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    target = models.DecimalField(max_digits=10, decimal_places=2)
    saved = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_date = models.DateTimeField(default=timezone.now)
    
    # check if done
    def is_achieved(self):
        return self.saved >= self.target if self.target > 0 else False
    
    def __str__(self):
        return self.name

class Transaction(models.Model): 
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)
    desc = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_income = models.BooleanField(default=False)  # True=income False=expense
    date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.desc} ${self.amount}"

class Subscription(models.Model):
    budget = models.ForeignKey('Budget', on_delete=models.CASCADE, related_name='subscriptions')

    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # keep it simple: monthly subscriptions (Netflix, Spotify, etc.)
    billing_day = models.PositiveSmallIntegerField(default=1)  # 1..28 recommended

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.amount}"