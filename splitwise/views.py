from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CreateGroupForm, SettleForm
from .models import (
    SplitGroup,
    GroupMember,
    SplitExpense,
    SplitExpenseShare,
    FriendRequest,
    get_friends,
)

User = get_user_model()

def _require_member(request, group: SplitGroup) -> bool:
    return GroupMember.objects.filter(group=group, user=request.user).exists()


def calculate_settlements(balances):
    """Compute an 'optimized' settlement suggestion from per-user net balances.

    NOTE: This collapses many-to-many relationships into a minimal set of
    payments. For a per-pair ledger (A↔B, A↔C, ...), use
    `calculate_pairwise_ledger` instead.
    """
    debtors = []
    creditors = []

    for b in balances:
        if b["net"] < 0:
            debtors.append({
                "user": b["user"],
                "amount": -b["net"],
            })
        elif b["net"] > 0:
            creditors.append({
                "user": b["user"],
                "amount": b["net"],
            })

    payments = []
    i = j = 0

    while i < len(debtors) and j < len(creditors):
        d = debtors[i]
        c = creditors[j]

        amt = min(d["amount"], c["amount"])

        payments.append({
            "from": d["user"],
            "to": c["user"],
            "amount": amt,
        })

        d["amount"] -= amt
        c["amount"] -= amt

        if d["amount"] == 0:
            i += 1
        if c["amount"] == 0:
            j += 1

    return payments


def calculate_pairwise_ledger(group, members):
    """Build a per-pair ledger of who owes whom, and per-user net balances.

    This keeps distinct relationships between users instead of collapsing
    everything into a single optimized set of transfers. If A owes both B and C,
    that will be represented as two separate entries.
    """
    # Map id -> User for quick lookup
    member_map = {m.id: m for m in members}

    # (debtor_id, creditor_id) -> Decimal total
    pair_totals = {}
    # per-user net: positive => others owe them, negative => they owe others
    net_map = {m.id: Decimal("0") for m in members}

    shares = (
        SplitExpenseShare.objects
        .filter(expense__group=group)
        .select_related("expense", "user", "expense__paid_by")
    )

    for share in shares:
        debtor_id = share.user_id
        creditor_id = share.expense.paid_by_id

        # Skip self-debts (when someone is both payer and participant) for pairs,
        # but they still don't change the net between different people.
        if debtor_id == creditor_id:
            continue

        key = (debtor_id, creditor_id)
        pair_totals[key] = pair_totals.get(key, Decimal("0")) + share.share_amount

        # Update per-user net balances from the same data source.
        net_map[debtor_id] -= share.share_amount
        net_map[creditor_id] += share.share_amount

    # Now net each unordered pair so we don't show both A→B and B→A.
    pair_ledger = []
    seen = set()

    for (debtor_id, creditor_id), amount_ab in pair_totals.items():
        if (debtor_id, creditor_id) in seen:
            continue

        amount_ba = pair_totals.get((creditor_id, debtor_id), Decimal("0"))
        net = amount_ab - amount_ba

        if net > 0:
            pair_ledger.append({
                "from": member_map[debtor_id],
                "to": member_map[creditor_id],
                "amount": net,
            })
        elif net < 0:
            pair_ledger.append({
                "from": member_map[creditor_id],
                "to": member_map[debtor_id],
                "amount": -net,
            })

        seen.add((debtor_id, creditor_id))
        seen.add((creditor_id, debtor_id))

    balances = [
        {"user": member_map[user_id], "net": net}
        for user_id, net in net_map.items()
    ]

    return pair_ledger, balances

@login_required
def dashboard(request):
    group_ids = GroupMember.objects.filter(
        user=request.user
    ).values_list("group_id", flat=True)

    groups = SplitGroup.objects.filter(
        id__in=group_ids
    ).order_by("-created_at")

    return render(request, "splitwise/dashboard.html", {
        "groups": groups,
    })


@login_required
def friends_list(request):
    friends = get_friends(request.user)
    incoming = FriendRequest.objects.filter(
        to_user=request.user,
        accepted=False,
    )
    outgoing = FriendRequest.objects.filter(
        from_user=request.user,
        accepted=False,
    )

    return render(request, "splitwise/friends_list.html", {
        "friends": friends,
        "incoming": incoming,
        "outgoing": outgoing,
    })


@login_required
def send_friend_request(request):
    if request.method != "POST":
        return redirect("splitwise:friends_list")

    identifier = request.POST.get("identifier", "").strip()

    if not identifier:
        messages.error(request, "Enter a username or email.")
        return redirect("splitwise:friends_list")

    target = (
        User.objects.filter(username__iexact=identifier).first()
        or User.objects.filter(email__iexact=identifier).first()
    )

    if not target or target == request.user:
        messages.error(request, "Invalid user.")
        return redirect("splitwise:friends_list")

    fr, created = FriendRequest.objects.get_or_create(
        from_user=request.user,
        to_user=target,
        defaults={"accepted": False},
    )

    if not created:
        messages.info(request, "Friend request already sent.")
    else:
        messages.success(request, "Friend request sent.")

    return redirect("splitwise:friends_list")


@login_required
def respond_friend_request(request, request_id, action):
    fr = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user,
    )

    if action == "accept":
        fr.accepted = True
        fr.save(update_fields=["accepted"])
        messages.success(request, "Friend request accepted.")
    elif action == "decline":
        fr.delete()
        messages.info(request, "Friend request declined.")

    return redirect("splitwise:friends_list")


@login_required
def group_create(request):
    if request.method == "POST":
        form = CreateGroupForm(request.user, request.POST)
        if form.is_valid():
            data = form.cleaned_data

            group = SplitGroup.objects.create(
                name=data["name"],
                created_by=request.user,
            )

            group.members.set(data["members"])

            GroupMember.objects.create(
                group=group,
                user=request.user,
                is_admin=True,
            )

            return redirect("splitwise:group_detail", group_id=group.id)
    else:
        form = CreateGroupForm(request.user)

    return render(request, "splitwise/group_create.html", {
        "form": form,
    })


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)

    if not _require_member(request, group):
        messages.error(request, "You are not a member of this group.")
        return redirect("splitwise:dashboard")

    members = User.objects.filter(
        split_memberships__group=group
    ).distinct()

    paid = (
        SplitExpense.objects
        .filter(group=group)
        .values("paid_by")
        .annotate(total=Sum("amount"))
    )
    paid_map = {
        r["paid_by"]: r["total"] or Decimal("0")
        for r in paid
    }

    # Per-user net balances and per-pair ledger computed from the same
    # underlying data so they are always consistent.
    payments, balances = calculate_pairwise_ledger(group, members)

    return render(request, "splitwise/group_detail.html", {
        "group": group,
        "members": members,
        "balances": balances,
        "payments": payments,
    })


@login_required
def add_member(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)

    if not _require_member(request, group):
        messages.error(request, "You are not a member of this group.")
        return redirect("splitwise:dashboard")

    friends = get_friends(request.user)

    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()

        if not identifier:
            messages.error(request, "Enter a username or email.")
            return redirect("splitwise:add_member", group_id=group.id)

        user = (
            friends.filter(username__iexact=identifier).first()
            or friends.filter(email__iexact=identifier).first()
        )

        if not user:
            messages.error(request, "No such friend. Add them as a friend first.")
            return redirect("splitwise:add_member", group_id=group.id)

        GroupMember.objects.get_or_create(
            group=group,
            user=user,
        )

        return redirect("splitwise:group_detail", group_id=group.id)

    return render(request, "splitwise/add_member.html", {
        "group": group,
    })


@login_required
def add_expense(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)

    if not _require_member(request, group):
        messages.error(request, "You are not a member of this group.")
        return redirect("splitwise:dashboard")

    members = User.objects.filter(
        split_memberships__group=group
    ).distinct()

    if request.method == "POST":
        description = request.POST.get("description", "").strip()
        raw_amount = request.POST.get("amount", "").strip()
        paid_by_id = request.POST.get("paid_by")
        participant_ids = request.POST.getlist("participants")

        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            messages.error(request, "Enter a valid amount.")
            return redirect("splitwise:add_expense", group_id=group.id)

        if amount <= 0:
            messages.error(request, "Amount must be positive.")
            return redirect("splitwise:add_expense", group_id=group.id)

        paid_by = User.objects.filter(
            id=paid_by_id,
            split_memberships__group=group,
        ).first()

        participants = User.objects.filter(
            id__in=participant_ids,
            split_memberships__group=group,
        ).distinct()

        if not paid_by or not participants.exists():
            messages.error(request, "Invalid payer or participants.")
            return redirect("splitwise:add_expense", group_id=group.id)

        split = (amount / participants.count()).quantize(Decimal("0.01"))

        with transaction.atomic():
            exp = SplitExpense.objects.create(
                group=group,
                paid_by=paid_by,
                description=description,
                amount=amount,
            )

            SplitExpenseShare.objects.bulk_create([
                SplitExpenseShare(
                    expense=exp,
                    user=u,
                    share_amount=split,
                )
                for u in participants
            ])

        return redirect("splitwise:group_detail", group_id=group.id)

    return render(request, "splitwise/add_expense.html", {
        "group": group,
        "members": members,
    })



@login_required
def settle(request, group_id):
    print(request.method)
    print(request.META.get("CONTENT_TYPE"))
    print(request.POST)
    group = get_object_or_404(SplitGroup, id=group_id)
    
    if not _require_member(request, group):
        messages.error(request, "You are not a member of this group.")
        return redirect("splitwise:dashboard")
    
    members = User.objects.filter(split_memberships__group=group).distinct()
    
    # GET request - show the settle form page
    if request.method == "GET":
        return render(request, "splitwise/settle.html", {
            "group": group,
            "members": members,
        })
    
    # POST request - process the settlement
    form = SettleForm(request.POST, group=group)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect("splitwise:group_detail", group_id=group_id)
    
    from_user = form.cleaned_data["from_user"]
    to_user = form.cleaned_data["to_user"]
    amount = form.cleaned_data["amount"]
    
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

    
    
    messages.success(request, "Settlement recorded.")
    return redirect("splitwise:group_detail", group_id=group_id)