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
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token
from django.db.models import Q, Count, Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse

logger = logging.getLogger(__name__)


# Create your views here.

class RequestOTPAPIView(APIView):
    permission_classes = (AllowAny,)
    
    @extend_schema(
        summary="درخواست کد تأیید (OTP)",
        description="یک کد ۶ رقمی به شماره تلفن وارد شده ارسال می‌شود. از این endpoint برای شروع فرآیند ورود استفاده کنید.",
        request=serializers.RequestOTPSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.RequestOTPSerializer,
                description="کد OTP با موفقیت ارسال شد",
                examples=[
                    OpenApiExample(
                        "موفقیت‌آمیز",
                        value={
                            "message": "کد تأیید با موفقیت ارسال شد",
                            "phone": "989123456789"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="خطا در اعتبارسنجی شماره تلفن"),
        },
        tags=["احراز هویت"],
        operation_id="request_otp/",
    )
    def post(self, request, *args, **kwargs):
        serializer = serializers.RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            otp, created = OTP.objects.get_or_create(phone=phone)
            otp.code = str(random.randint(100000, 999999))
            otp.created_at = timezone.now()
            otp.save()
            
            logger.info(f"OTP for {phone}: {otp.code}")
            
            return Response({
                'message': "OTP send su ccessfully",
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


    @extend_schema(
        summary="تأیید کد OTP و ورود",
        description="کد ۶ رقمی دریافتی را به همراه شماره تلفن ارسال کنید. در صورت موفقیت، توکن احراز هویت دریافت می‌کنید.",
        parameters=[
            OpenApiParameter(
                name='phone',
                location=OpenApiParameter.PATH,
                description="شماره تلفن کاربر (همان شماره‌ای که کد به آن ارسال شده)",
                required=True,
                type=str,
                examples=[
                    OpenApiExample(
                        "شماره نمونه",
                        value="989123456789"
                    )
                ]
            ),
        ],
        request=serializers.VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="ورود موفقیت‌آمیز",
                examples=[
                    OpenApiExample(
                        "پروفایل تکمیل شده",
                        value={
                            "message": "ورود موفقیت‌آمیز بود.",
                            "redirect_url": "home",
                            "user_id": 1,
                            "token": "a1b2c3d4e5f6...",
                            "profile_completed": True
                        }
                    ),
                    OpenApiExample(
                        "نیاز به تکمیل پروفایل",
                        value={
                            "message": "لطفاً پروفایل خود را تکمیل کنید.",
                            "redirect_url": "setup_profile",
                            "user_id": 2,
                            "token": "f6e5d4c3b2a1...",
                            "profile_completed": False
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="کد منقضی شده یا نادرست"),
            404: OpenApiResponse(description="کد تأیید یافت نشد"),
        },
        tags=["احراز هویت"],
        operation_id="verify_otp",
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
            'token': token.key,
            'profile_completed': bool(profile.name)
        }, status=status.HTTP_200_OK)


class SetupProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]


    @extend_schema(
        summary="تکمیل پروفایل کاربر",
        description="پس از اولین ورود، اطلاعات پروفایل خود را تکمیل کنید. این endpoint فقط برای کاربرانی که پروفایل ندارند قابل استفاده است.",
        request=serializers.SetupProfileSerializer,
        responses={
            200: OpenApiResponse(
                description="پروفایل با موفقیت تکمیل شد",
                examples=[
                    OpenApiExample(
                        "موفقیت‌آمیز",
                        value={
                            "message": "پروفایل با موفقیت تکمیل شد.",
                            "redirect_url": "home",
                            "profile": {
                                "name": "علی محمدی",
                                "phone": "989123456789",
                            },
                            "profile_completed": True
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="خطا در اطلاعات وارد شده"),
            401: OpenApiResponse(description="لطفاً ابتدا وارد شوید"),
        },
        tags=["پروفایل"],
        operation_id="setup_profile",
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
    
    
    @extend_schema(
        summary="مشاهده پروفایل",
        description="پروفایل کاربر را با تب‌های مختلف (پست‌ها، پاسخ‌ها، رسانه‌ها، لایک‌ها) مشاهده کنید.",
        parameters=[
            OpenApiParameter(
                name='username',
                location=OpenApiParameter.QUERY,
                description="نام کاربری برای مشاهده (اختیاری - اگر وارد نشود پروفایل خودتان نمایش داده می‌شود)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='tab',
                location=OpenApiParameter.QUERY,
                description="تب مورد نظر برای نمایش",
                required=False,
                type=str,
                enum=['posts', 'replies', 'media', 'likes'],
                default='posts',
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="اطلاعات پروفایل",
                examples=[
                    OpenApiExample(
                        "پروفایل کامل",
                        value={
                            "profile": {
                                "id": 1,
                                "name": "علی محمدی",
                                "phone": "989123456789",
                            },
                            "tweets": [],
                            "active_tab": "posts",
                            "tweets_count": 0
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description="لطفاً ابتدا وارد شوید"),
            404: OpenApiResponse(description="کاربر یافت نشد"),
        },
        tags=["پروفایل"],
        operation_id="view_profile",
    )

    def get(self, request, username=None):
        if username:
            user_instance = get_object_or_404(User, username=username)
            profile_instance = get_object_or_404(Profile, user=user_instance)
        else:
            user_instance = request.user
            profile_instance = get_object_or_404(Profile, user=user_instance)

        profile_serializer = serializers.UserProfileSerializer(profile_instance)

        active_tab = request.GET.get('tab', 'posts')
        tweets_qs = None

        if active_tab == 'posts':
            tweets_qs = Tweets.objects.filter(user=user_instance, parent__isnull=True)
        elif active_tab == 'replies':
            tweets_qs = Tweets.objects.filter(user=user_instance, parent__isnull=False)
        elif active_tab == 'media':
            tweets_qs = Tweets.objects.filter(user=user_instance, parent__isnull=True).filter(
                Q(image__isnull=False) | Q(video__isnull=False)
            )
        elif active_tab == 'likes':
            liked_tweet_ids = Like.objects.filter(user=user_instance).values_list('tweet_id', flat=True)
            tweets_qs = Tweets.objects.filter(id__in=liked_tweet_ids, parent__isnull=True)
        else:
            tweets_qs = Tweets.objects.filter(user=user_instance, parent__isnull=True)

        tweets_qs = tweets_qs.select_related('user__profile').annotate(
            likes_count_annotate=Count('likes', distinct=True),
            comments_count_annotate=Count('comments', distinct=True)
        ).order_by('-created_at')

        for tweet in tweets_qs:
            tweet.user_liked = Like.objects.filter(user=request.user, tweet=tweet).exists()

        tweets_serializer = serializers.PostsSerializer(tweets_qs, many=True, context={'request': request})

        return Response({
            'profile': profile_serializer.data,
            'tweets': tweets_serializer.data,
            'active_tab': active_tab,
        })
        