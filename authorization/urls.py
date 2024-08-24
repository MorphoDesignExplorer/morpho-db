from django.urls import path

from authorization import views

urlpatterns = [
    path('/init', views.AuthInitView.as_view()),
    path('/verify', views.AuthVerifyView.as_view()),
    path('/refresh_secret', views.AuthRefreshSecretView.as_view()),
    path('/reset_password_init', views.AuthInitiateResetPasswordView.as_view()),
    path('/reset_password', views.AuthResetPasswordView.as_view())
]
