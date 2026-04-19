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
from core.models import OTP

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