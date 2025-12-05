from django.urls import path, include
from .views import Customers

urlpatterns = [
    path("customers/", Customers.as_view()),
    # path("test/", Test.as_view())
]
