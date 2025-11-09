from django.urls import path
from . import views

urlpatterns = [

    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("favorites/", views.favorites_list, name="favorites"),
    path("favorites/clear/", views.clear_favorites, name="clear_favorites"),


]