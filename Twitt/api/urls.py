from django.urls import path
from . import views

urlpatterns = [
    #login
    path('request_otp/', views.RequestOTPAPIView.as_view(), name='request_otp'), 
    path('verify_otp/'  , views.VerifyOTPAPIView.as_view() , name="verify_otp"),
    
    
    #Profile
    path('profileView/', views.ProfileAPIView.as_view(), name='ProfileView'),
    path('stup_Profile/' , views.SetupProfileAPIView.as_view() , name="stup_Profile")
    
    
]