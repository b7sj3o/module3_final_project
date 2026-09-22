from django.urls import path

from .views import ReviewCreateView

app_name = "reviews"

urlpatterns = [
    path("product/<slug:slug>/review/", ReviewCreateView.as_view(), name="create"),
]
