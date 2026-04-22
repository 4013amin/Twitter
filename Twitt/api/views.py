from datetime import timedelta
from xml import parsers
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
import random
import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from . import serializers
import logging
from core.models import OTP, User, Tweets, Profile, Like, Follow, Comment
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import UserProfileSerializer

logger = logging.getLogger(__name__)


# Create your views here.

class RequestOTPAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = serializers.RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            otp, created = OTP.objects.get_or_create(phone=phone)
            otp.code = str(random.randint(100000, 999999))
            otp.created_at = timezone.now()
            otp.save()

            # Send SMS Method (placeholder)

            return Response({
                'message': "OTP send successfully",
                'phone': phone
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPAPIView(APIView):

    def post(self, request, phone, *args, **kwargs):
        serializer = serializers.VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']

        try:
            otp = get_object_or_404(OTP, phone=phone, code=code)
        except OTP.DoesNotExist:
            return Response(
                {'error': 'کد تایید نادرست است.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if otp.created_at < timezone.now() - timedelta(minutes=2):
            otp.delete()
            return Response(
                {'error': 'کد منقضی شده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp.delete()

        user = User.objects.filter(username=phone).first()
        if not user:
            user = User.objects.create_user(username=phone)

        profile = Profile.objects.filter(user=user).first()
        if not profile:
            existing_profile = Profile.objects.filter(phone=phone).first()
            if existing_profile:
                existing_profile.user = user
                existing_profile.save()
                profile = existing_profile
            else:
                profile = Profile.objects.create(
                    user=user,
                    phone=phone,
                    name=''
                )

        login(request, user)

        if profile.name:
            redirect_url = 'home'
            message = 'ورود موفقیت‌آمیز بود.'
        else:
            redirect_url = 'setup_profile'
            message = 'لطفاً پروفایل خود را تکمیل کنید.'

        return Response({
            'message': message,
            'redirect_url': redirect_url,
            'user_id': user.id,
            'profile_completed': bool(profile.name)
        }, status=status.HTTP_200_OK)


class SetupProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        profile, created = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                'phone': request.user.username,
                'name': ''
            }
        )

        if profile.name:
            return Response(
                {
                    'message': 'پروفایل قبلاً تکمیل شده است.',
                    'redirect_url': 'home',
                    'profile_completed': True
                },
                status=status.HTTP_200_OK
            )

        serializer = serializers.SetupProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        profile.name = serializer.validated_data.get('name', profile.name)

        new_phone = serializer.validated_data.get('phone')
        if new_phone and new_phone != profile.phone:
            if Profile.objects.exclude(pk=profile.pk).filter(phone=new_phone).exists():
                return Response(
                    {'error': 'این شماره تلفن قبلاً توسط کاربر دیگری استفاده شده است.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            profile.phone = new_phone

        profile.save()

        return Response(
            {
                'message': 'پروفایل با موفقیت تکمیل شد.',
                'redirect_url': 'home',
                'profile': {
                    'name': profile.name,
                    'phone': profile.phone,
                    # 'bio': profile.bio,
                },
                'profile_completed': True
            },
            status=status.HTTP_200_OK
        )


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username=None):
        if username:
            profile = get_object_or_404(User, username=username)
        else:
            profile = Profile.objects.filter(user=request.user).first()

        profile_serializer = UserProfileSerializer(profile)
