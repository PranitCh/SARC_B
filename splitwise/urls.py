from django.urls import path
from . import views

app_name = "splitwise"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("friends/", views.friends_list, name="friends_list"),
    path("friends/send/", views.send_friend_request, name="send_friend_request"),
    path(
        "friends/<int:request_id>/<str:action>/",
        views.respond_friend_request,
        name="respond_friend_request",
    ),
    path("groups/new/", views.group_create, name="group_create"),
    path("groups/<int:group_id>/", views.group_detail, name="group_detail"),
    path("groups/<int:group_id>/add-member/", views.add_member, name="add_member"),
    path("groups/<int:group_id>/add-expense/", views.add_expense, name="add_expense"),
    path("groups/<int:group_id>/settle/", views.settle, name="settle"),
]
