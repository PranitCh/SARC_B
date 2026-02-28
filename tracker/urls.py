"""
URL configuration for tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from expenses.views import BudgetViewSet, TransactionViewSet, GoalViewSet, SubscriptionViewSet
from splitwise.api_views import (
    SplitGroupViewSet,
    SplitExpenseViewSet,
    GroupMemberViewSet,
    SplitExpenseShareViewSet,
    FriendRequestViewSet,
)
router = DefaultRouter()
router.register(r'budgets', BudgetViewSet, basename='budeget')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r"splitwise/groups", SplitGroupViewSet, basename="sw-groups")
router.register(r"splitwise/members", GroupMemberViewSet, basename="sw-members")
router.register(r"splitwise/expenses", SplitExpenseViewSet, basename="sw-expenses")
router.register(r"splitwise/shares", SplitExpenseShareViewSet, basename="sw-shares")
router.register(r"splitwise/friend-requests", FriendRequestViewSet, basename="sw-friend-requests")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expenses.urls')),
    path('api/', include(router.urls)),
    path("splitwise/", include("splitwise.urls")),
    path('accounts/', include('django.contrib.auth.urls')),
]