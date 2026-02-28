from decimal import Decimal
from rest_framework import serializers
from .models import (
    SplitGroup, GroupMember, SplitExpense, SplitExpenseShare, FriendRequest
)

class SplitGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SplitGroup
        fields = ["id", "name", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]


class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = ["id", "group", "user", "is_admin", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class SplitExpenseShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = SplitExpenseShare
        fields = ["id", "expense", "user", "share_amount"]
        read_only_fields = ["id"]


class SplitExpenseSerializer(serializers.ModelSerializer):
    # Optional: include shares in responses
    shares = SplitExpenseShareSerializer(many=True, read_only=True)

    class Meta:
        model = SplitExpense
        fields = ["id", "group", "paid_by", "description", "amount", "created_at", "shares"]
        read_only_fields = ["id", "created_at"]


class FriendRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendRequest
        fields = ["id", "from_user", "to_user", "created_at", "accepted"]
        read_only_fields = ["id", "from_user", "created_at", "accepted"]