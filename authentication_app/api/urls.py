from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView

urlpatterns = [
    # POST: { "username": "...", "password": "..." }
    path("login/", TokenObtainPairView.as_view(), name="login"),

    # OPTIONAL: falls Angular Token erneuern möchte
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # GET: Informationen über den eingeloggten User
    path("me/", MeView.as_view(), name="me"),
]
