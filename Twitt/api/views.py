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
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token


logger = logging.getLogger(__name__)


# Create your views here.

class RequestOTPAPIView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="ارسال کد تأیید (OTP) به شماره تلفن",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone'],
            properties={
                'phone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='شماره تلفن همراه (با پیشوند کد کشور)',
                    example='989123456789'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='کد OTP با موفقیت ارسال شد',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'phone': openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(description='خطا در اعتبارسنجی'),
        },
        tags=['احراز هویت'],
    )
    def post(self, request, *args, **kwargs):
        serializer = serializers.RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            otp, created = OTP.objects.get_or_create(phone=phone)
            otp.code = str(random.randint(100000, 999999))
            otp.created_at = timezone.now()
            otp.save()
            return Response({
                'message': "OTP send successfully",
                'phone': phone
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class VerifyOTPAPIView(APIView):
    permission_classes = (AllowAny,)

    phone_param = openapi.Parameter(
        'phone',
        openapi.IN_PATH,
        description="شماره تلفن کاربر",
        type=openapi.TYPE_STRING,
        example='989123456789'
    )

    @swagger_auto_schema(
        operation_description="تأیید کد OTP و ورود به سیستم",
        manual_parameters=[phone_param],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['code'],
            properties={
                'code': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='کد ۶ رقمی ارسال شده به تلفن',
                    example='123456'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='ورود موفقیت‌آمیز',
                examples={
                    'application/json': {
                        'message': 'ورود موفقیت‌آمیز بود.',
                        'redirect_url': 'home',
                        'user_id': 1,
                        'profile_completed': True
                    }
                },
            ),
            400: openapi.Response(
                description='کد منقضی شده',
                examples={
                    'application/json': {
                        'error': 'کد منقضی شده است.'
                    }
                },
            ),
            404: openapi.Response(
                description='کد نادرست',
                examples={
                    'application/json': {
                        'error': 'کد تایید نادرست است.'
                    }
                },
            ),
        },
        tags=['احراز هویت'],
    )
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
            
            
        token, created = Token.objects.get_or_create(user=user)
        
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
            'token': token.key ,
            'profile_completed': bool(profile.name)
        }, status=status.HTTP_200_OK)



class SetupProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="تکمیل اطلاعات پروفایل کاربر (فقط برای کاربران جدید)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name'],
            properties={
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='نام و نام خانوادگی کاربر',
                    example='علی محمدی'
                ),
                'phone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='شماره تلفن همراه (اختیاری)',
                    example='989123456789'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='پروفایل با موفقیت تکمیل شد',
                examples={
                    'application/json': {
                        'message': 'پروفایل با موفقیت تکمیل شد.',
                        'redirect_url': 'home',
                        'profile': {
                            'name': 'علی محمدی',
                            'phone': '989123456789',
                        },
                        'profile_completed': True
                    }
                },
            ),
            400: openapi.Response(description='خطا در اعتبارسنجی'),
            401: openapi.Response(description='احراز هویت نشده'),
        },
        tags=['پروفایل'],
    )
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
                },
                'profile_completed': True
            },
            status=status.HTTP_200_OK
        )


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    username_param = openapi.Parameter(
        'username',
        openapi.IN_QUERY,
        description="نام کاربری (اختیاری - اگر وارد نشود، پروفایل خود کاربر برگردانده می‌شود)",
        type=openapi.TYPE_STRING,
        example='989123456789'
    )

    @swagger_auto_schema(
        operation_description="دریافت اطلاعات پروفایل کاربر",
        manual_parameters=[username_param],
        responses={
            200: openapi.Response(
                description='اطلاعات پروفایل',
                examples={
                    'application/json': {
                        'profile': {
                            'id': 1,
                            'name': 'علی محمدی',
                            'phone': '989123456789',
                        }
                    }
                },
            ),
            401: openapi.Response(description='احراز هویت نشده'),
            404: openapi.Response(description='کاربر یافت نشد'),
        },
        tags=['پروفایل'],
    )
    def get(self, request, username=None):
        
        if username:
            profile = get_object_or_404(User, username=username)
        else:
            profile = Profile.objects.filter(user=request.user).first()
            
        profile_serializer = UserProfileSerializer(profile)
        
        return Response({
            'profile': profile_serializer.data
        })