from django.urls import path
from . import views

urlpatterns = [
    path('request_otp/', views.RequestOTPAPIView.as_view(), name='request_otp'),  
    path('verify-otp/<str:phone>/', views.VerifyOTPAPIView.as_view(), name='verify_otp'),
    
    path('profileView/', views.ProfileAPIView.as_view(), name='ProfileView'),
]
