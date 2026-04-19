from rest_framework import serializers
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiTypes, extend_schema_field
from core.models import OTP


class RequestOTPSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=11)

    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError("لطفاً یک شماره موبایل معتبر (مانند 09123456789) وارد کنید.")
        return value
