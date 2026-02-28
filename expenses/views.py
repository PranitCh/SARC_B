# expense tracker - sarc project, no slugs anymore lol
#transactions refresh after save + full debug + all handlers

from django.shortcuts import render, get_object_or_404, redirect  
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.views.decorators.cache import never_cache
from django.db.models import Sum
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from rest_framework import viewsets
from .serializers import BudgetSerializer, TransactionSerializer, GoalSerializer, SubscriptionSerializer
from .models import Budget, Goal, Transaction, Subscription
from .forms import BudgetForm, GoalForm, TransactionForm, SubscriptionForm, CustomUserCreationForm, CustomAuthenticationForm
from decimal import Decimal
import random
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

def user_login(request):
    print(f"LOGIN VIEW - Method: {request.method}")

    form = CustomAuthenticationForm()
    if request.method == 'POST':
        print("POST DATA:", request.POST)
        form = CustomAuthenticationForm(request, data=request.POST)
        print(f"Form valid: {form.is_valid()}")

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            print(f"Attempting to authenticate: {username}")
            user = authenticate(username=username, password=password)
            print(f"User object: {user}")

            if user is not None:
                login(request, user)
                print(f"User logged in: {username}")
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'registration/login.html', {'form': form})

def register(request):
    form_data = CustomUserCreationForm()
    if request.method == 'POST':
        form_data = CustomUserCreationForm(request.POST)
        if form_data.is_valid():
            user = form_data.save()
            login(request, user)
            print("new user registered:", user.username)
            return redirect('dashboard')
    return render(request, 'register.html', {'form': form_data})

@login_required
@never_cache
def home_dashboard(request):
    quotes = [
        {
            'text': "The secret of getting ahead is getting started.",
            'author': "Mark Twain",
            'emoji': "💡"
        },
        {
            'text': "Success is not final, failure is not fatal: it is the courage to continue that counts.",
            'author': "Winston Churchill",
            'emoji': "🎯"
        },
        {
            'text': "The only way to do great work is to love what you do.",
            'author': "Steve Jobs",
            'emoji': "❤️"
        },
        {
            'text': "Believe you can and you're halfway there.",
            'author': "Theodore Roosevelt",
            'emoji': "⭐"
        },
        {
            'text': "Don't watch the clock; do what it does. Keep going.",
            'author': "Sam Levenson",
            'emoji': "⏰"
        },
        {
            'text': "The best time to plant a tree was 20 years ago. The second best time is now.",
            'author': "Chinese Proverb",
            'emoji': "🌱"
        },
        {
            'text': "Your limitation—it's only your imagination.",
            'author': "Unknown",
            'emoji': "✨"
        },
        {
            'text': "Great things never come from comfort zones.",
            'author': "Unknown",
            'emoji': "🚀"
        },
    ]
    
    daily_quote = random.choice(quotes)

    print(f"🎲 Selected quote: {daily_quote['text'][:30]}... by {daily_quote['author']}")
    
    return render(request, 'home_dashboard.html', {
        'quote': daily_quote
    })

@login_required
def toggle_dark_mode(request):
    if 'dark_mode' in request.session:
        request.session['dark_mode'] = not request.session['dark_mode']
    else:
        request.session['dark_mode'] = True
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def dashboard(request):
    print("🚀 DASHBOARD VIEW HIT!")
    budgets = Budget.objects.filter(user=request.user)
    budget_form = BudgetForm()
    
    if request.method == 'POST':
        budget_form = BudgetForm(request.POST)
        if budget_form.is_valid():
            budget = budget_form.save(commit=False)
            budget.user = request.user  
            budget.save()
            messages.success(request, 'Budget created succesfully!')
            print(f"budget saved: {budget.name}")
    
    return render(request, 'dashboard.html', {
        'budgets': budgets,
        'budget_form': budget_form
    })


@login_required  
def budget_detail(request, pk):
    budget_obj = get_object_or_404(Budget, pk=pk, user=request.user)
    goals = Goal.objects.filter(budget=budget_obj)
    transactions = Transaction.objects.filter(budget=budget_obj).order_by('-id')
    
    # forms for template
    budget_form = BudgetForm(instance=budget_obj)
    goal_form = GoalForm()
    trans_form = TransactionForm()

    subs = Subscription.objects.filter(budget=budget_obj).order_by('-id')
    sub_form = SubscriptionForm()
    
    print(f"Loading {budget_obj.name} (pk={pk})")
    
    if request.method == 'POST':
        print("POST KEYS:", list(request.POST.keys()))
        
        # updating budget query
        if request.POST.get('save_budget'):
            print("BUDGET UPDATE")
            budget_form = BudgetForm(request.POST, instance=budget_obj)
            if budget_form.is_valid():
                budget_form.save()
                print("BUDGET UPDATED")
                messages.success(request, 'Budget updated!')
            return redirect('budget_detail', pk=pk)
        
        # adding goal query
        if request.POST.get('save_goal'):
            print("ADD GOAL")
            temp_goal_form = GoalForm(request.POST)
            if temp_goal_form.is_valid():
                goal_record = temp_goal_form.save(commit=False)
                goal_record.budget = budget_obj
                goal_record.save()
                goals = Goal.objects.filter(budget=budget_obj)
                print(f"GOAL SAVED: {goal_record.name}")
                messages.success(request, 'Goal added!')
            return redirect('budget_detail', pk=pk)
        
        # add transaction query
        if request.POST.get('save_trans'):
            print("ADD TRANSACTION")
            temp_trans_form = TransactionForm(request.POST)
            if temp_trans_form.is_valid():
                trans_rec = temp_trans_form.save(commit=False)
                trans_rec.budget = budget_obj
                trans_rec.save()
                print(f"TRANS SAVED ID:{trans_rec.id} '{trans_rec.desc}' ${trans_rec.amount}")
                
                transactions = Transaction.objects.filter(budget=budget_obj).order_by('-id')
                
                messages.success(request, 'Transaction added!')
            else:
                print("TRANS ERRORS:", temp_trans_form.errors)
            return redirect('budget_detail', pk=pk)
        
        # adding money query
        if request.POST.get('add_money'):
            print("ADD MONEY POST:", request.POST)
            try:
                goal_id = int(request.POST.get('goal_id'))
                amount_str = request.POST.get('amount', '0')
                amount = Decimal(amount_str)
        
                if amount <= 0:
                    messages.error(request, 'Amount must be positive!')
                    print("INVALID AMOUNT:", amount)
                else:
                    goal = Goal.objects.get(id=goal_id, budget=budget_obj)
                    goal.saved += amount
                    goal.save()
                    print(f"${amount} to {goal.name} (now ${goal.saved})")
                    messages.success(request, f'Added ${amount:.2f}!')
            except (ValueError, Goal.DoesNotExist):
                messages.error(request, 'Invalid goal or amount!')
                print("ADD MONEY ERROR")
            return redirect('budget_detail', pk=pk)

        
        # delete goal query
        if request.POST.get('delete_goal'):
            goal_id = request.POST.get('delete_goal')
            Goal.objects.filter(id=goal_id, budget=budget_obj).delete()
            goals = Goal.objects.filter(budget=budget_obj)
            print("GOAL DELETED")
            messages.info(request, 'Goal deleted')
            return redirect('budget_detail', pk=pk)
        
        # delete transaction query
        if request.POST.get('delete_trans'):
            trans_id = request.POST.get('delete_trans')
            Transaction.objects.filter(id=trans_id, budget=budget_obj).delete()
            transactions = Transaction.objects.filter(budget=budget_obj).order_by('-id')  # refreshing and sorting by id
            print("TRANS DELETED")
            messages.info(request, 'Transaction deleted')
            return redirect('budget_detail', pk=pk)
    
        # add subscription
        if request.POST.get('save_sub'):
            print("ADD SUBSCRIPTION")
            temp_sub_form = SubscriptionForm(request.POST)

            if temp_sub_form.is_valid():
                sub = temp_sub_form.save(commit=False)
                sub.budget = budget_obj
                sub.save()
                messages.success(request, 'Subscription added!')
            else:
                print("SUB ERRORS:", temp_sub_form.errors)
                messages.error(request, 'Subscription not added (invalid form).')

            return redirect('budget_detail', pk=pk)

# delete subscription (+ its linked transaction)
        if request.POST.get("delete_sub"):
            sub_id = request.POST.get("delete_sub")

            sub = Subscription.objects.filter(id=sub_id, budget=budget_obj).first()
            if not sub:
                messages.error(request, "Subscription not found.")
                return redirect("budget_detail", pk=pk)

    # If subscription has a linked transaction id, try deleting it (safe even if already deleted)
            if sub.transaction_id:
                Transaction.objects.filter(id=sub.transaction_id, budget=budget_obj).delete()

    # Always delete the subscription itself
            sub.delete()

            messages.info(request, "Subscription deleted.")
            return redirect("budget_detail", pk=pk)


    # calculating totals
    inc_amt = transactions.filter(is_income=True).aggregate(Sum('amount'))['amount__sum'] or 0
    exp_amt = transactions.filter(is_income=False).aggregate(Sum('amount'))['amount__sum'] or 0
    net_amt = inc_amt - exp_amt
    
    context = {
        'budget': budget_obj,
        'goals': goals,
        'transactions': transactions,
        'budget_form': budget_form,
        'goal_form': goal_form,
        'trans_form': trans_form,
        'total_income': inc_amt,
        'total_expenses': exp_amt,
        'net_amount': net_amt,
        'subscriptions': subs,
        'sub_form': sub_form,
    }
    
    return render(request, 'budget_detail.html', context)

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(budget__user=self.request.user)

    def perform_create(self, serializer):
        budget = serializer.validated_data.get("budget")
        if budget.user != self.request.user:
            raise PermissionDenied("Not your budget.")
        serializer.save()

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(budget__user=self.request.user)

    def perform_create(self, serializer):
        budget = serializer.validated_data.get("budget")
        if budget.user != self.request.user:
            raise PermissionDenied("Not your budget.")
        serializer.save()

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(budget__user=self.request.user)

    def perform_create(self, serializer):
        budget = serializer.validated_data.get("budget")
        if budget.user != self.request.user:
            raise PermissionDenied("Not your budget.")
        serializer.save()