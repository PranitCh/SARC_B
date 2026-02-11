from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint, Q

User = settings.AUTH_USER_MODEL

class SplitGroup(models.Model):
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_split_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    members = models.ManyToManyField(
        User,
        through="GroupMember",
        related_name="split_groups",
    )

class GroupMember(models.Model):
    group = models.ForeignKey(SplitGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="split_memberships")
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["group", "user"], name="uniq_group_user_membership")
        ]

class SplitExpense(models.Model):
    group = models.ForeignKey(SplitGroup, on_delete=models.CASCADE, related_name="expenses")
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="paid_split_expenses")
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class SplitExpenseShare(models.Model):
    expense = models.ForeignKey(SplitExpense, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="split_shares")
    share_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["expense", "user"], name="uniq_expense_user_share")
        ]
        

class FriendRequest(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friend_requests_sent",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friend_requests_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["from_user", "to_user"],
                name="uniq_friend_request",
            )
        ]

    def __str__(self) -> str:
        status = "accepted" if self.accepted else "pending"
        return f"{self.from_user} → {self.to_user} ({status})"


def get_friends(user):
    """Return queryset of users who are mutual friends with `user`."""
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    return UserModel.objects.filter(
        Q(friend_requests_sent__to_user=user, friend_requests_sent__accepted=True)
        | Q(friend_requests_received__from_user=user, friend_requests_received__accepted=True)
    ).distinct()