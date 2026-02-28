from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import SplitGroup, GroupMember, SplitExpense, SplitExpenseShare, FriendRequest
from .serializers import (
    SplitGroupSerializer,
    GroupMemberSerializer,
    SplitExpenseSerializer,
    SplitExpenseShareSerializer,
    FriendRequestSerializer,
)

User = get_user_model()

def calculate_pairwise_ledger(group, members):
    member_map = {m.id: m for m in members}
    pair_totals = {}
    net_map = {m.id: Decimal("0") for m in members}

    shares = (
        SplitExpenseShare.objects
        .filter(expense__group=group)
        .select_related("expense", "user", "expense__paid_by")
    )

    for share in shares:
        debtor_id = share.user_id
        creditor_id = share.expense.paid_by_id

        if debtor_id == creditor_id:
            continue

        key = (debtor_id, creditor_id)
        pair_totals[key] = pair_totals.get(key, Decimal("0")) + share.share_amount

        net_map[debtor_id] -= share.share_amount
        net_map[creditor_id] += share.share_amount

    pair_ledger = []
    seen = set()

    for (debtor_id, creditor_id), amount_ab in pair_totals.items():
        if (debtor_id, creditor_id) in seen:
            continue

        amount_ba = pair_totals.get((creditor_id, debtor_id), Decimal("0"))
        net = amount_ab - amount_ba

        if net > 0:
            pair_ledger.append({"from": debtor_id, "to": creditor_id, "amount": net})
        elif net < 0:
            pair_ledger.append({"from": creditor_id, "to": debtor_id, "amount": -net})

        seen.add((debtor_id, creditor_id))
        seen.add((creditor_id, debtor_id))

    balances = [{"user": uid, "net": net} for uid, net in net_map.items()]
    return pair_ledger, balances

def is_member(user, group_id):
    return GroupMember.objects.filter(group_id=group_id, user=user).exists()

def is_admin(user, group_id):
    return GroupMember.objects.filter(group_id=group_id, user=user, is_admin=True).exists()


class SplitGroupViewSet(viewsets.ModelViewSet):
    serializer_class = SplitGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SplitGroup.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        GroupMember.objects.get_or_create(
            group=group,
            user=self.request.user,
            defaults={"is_admin": True},
        )

    @action(detail=True, methods=["get"], url_path="balances")
    def balances(self, request, pk=None):
        group = self.get_object()  # already member-scoped by get_queryset()
        members = User.objects.filter(split_memberships__group=group).distinct()

        payments, balances = calculate_pairwise_ledger(group, members)

        # Optional: include username/email in response
        member_map = {u.id: u for u in members}
        balances_out = [
            {
                "user_id": b["user"],
                "username": getattr(member_map[b["user"]], "username", ""),
                "net": str(b["net"]),
            }
            for b in balances
        ]
        payments_out = [
            {
                "from_user_id": p["from"],
                "from_username": getattr(member_map[p["from"]], "username", ""),
                "to_user_id": p["to"],
                "to_username": getattr(member_map[p["to"]], "username", ""),
                "amount": str(p["amount"]),
            }
            for p in payments
        ]

        return Response(
            {
                "group_id": group.id,
                "group_name": group.name,
                "balances": balances_out,
                "payments": payments_out,
            },
            status=status.HTTP_200_OK,
        )


    @action(detail=True, methods=["post"], url_path="settle")
    def settle(self, request, pk=None):
        group = self.get_object()

        from_user_id = request.data.get("from_user")
        to_user_id = request.data.get("to_user")
        raw_amount = request.data.get("amount")

        if not from_user_id or not to_user_id or raw_amount is None:
            return Response(
                {"detail": "from_user, to_user, amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError):
            return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        # Both users must be group members
        if not GroupMember.objects.filter(group=group, user_id=from_user_id).exists():
            return Response({"detail": "from_user must be a group member."}, status=status.HTTP_400_BAD_REQUEST)

        if not GroupMember.objects.filter(group=group, user_id=to_user_id).exists():
            return Response({"detail": "to_user must be a group member."}, status=status.HTTP_400_BAD_REQUEST)

        from_user = User.objects.get(id=from_user_id)
        to_user = User.objects.get(id=to_user_id)

        with transaction.atomic():
            exp = SplitExpense.objects.create(
                group=group,
                paid_by=from_user,
                description=f"Settlement: {from_user.username} → {to_user.username}",
                amount=amount,
            )

        SplitExpenseShare.objects.create(
            expense=exp,
            user=to_user,
            share_amount=amount,
        )

        return Response(
            {
                "detail": "Settlement recorded.",
                "expense_id": exp.id,
                "group_id": group.id,
            },
            status=status.HTTP_201_CREATED,
        )


class GroupMemberViewSet(viewsets.ModelViewSet):
    serializer_class = GroupMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = GroupMember.objects.filter(group__members=self.request.user).distinct()
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]
        if not is_admin(self.request.user, group.id):
            raise PermissionDenied("Only group admins can add members.")
        serializer.save()


class SplitExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = SplitExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SplitExpense.objects.filter(group__members=self.request.user).distinct()
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]
        if not is_member(self.request.user, group.id):
            raise PermissionDenied("You are not a member of this group.")
        serializer.save()


class SplitExpenseShareViewSet(viewsets.ModelViewSet):
    serializer_class = SplitExpenseShareSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SplitExpenseShare.objects.filter(expense__group__members=self.request.user).distinct()
        expense_id = self.request.query_params.get("expense")
        if expense_id:
            qs = qs.filter(expense_id=expense_id)
        return qs


class FriendRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (FriendRequest.objects.filter(from_user=self.request.user) |
                FriendRequest.objects.filter(to_user=self.request.user))

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)