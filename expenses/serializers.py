from rest_framework import serializers
from .models import Budget, Goal, Transaction, Subscription

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['name', 'amount']

class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['name', 'target']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['desc', 'amount', 'is_income']

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'name', 'amount', 'billing_day', 'is_active', 'created_at', 'budget', 'transaction']