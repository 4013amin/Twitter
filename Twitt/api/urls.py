from django.urls import path
from . import views

urlpatterns = [
    path('request_otp/ ', views.RequestOTPAPIView.as_view(), name='request_otp'),
]
