from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.dashboard, name='dashboard'),
    path('budget/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('toggle-dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode'),

]
