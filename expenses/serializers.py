from rest_framework import serializers
from .models import Budget, Goal, Transaction, Subscription

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'name', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']

class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'name', 'target', 'saved', 'created_date', 'budget']
        read_only_fields = ['id', 'saved', 'created_date']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'desc', 'amount', 'is_income', 'date', 'budget']
        fields = ['desc', 'amount', 'is_income']

class SubscriptionSerializer(serializers.ModelSerializer):
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id',
            'name',
            'amount',
            'billing_day',
            'is_active',
            'created_at',
            'budget',
            'transaction',
            'total_cost',
        ]
        read_only_fields = ['id', 'created_at', 'transaction']

    def get_total_cost(self, obj):
        return obj.total_cost()