from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from . import models


class register_otp_form(forms.Form):
    phone = forms.CharField(
        max_length=10,
        label='شماره تلفن',
        widget=forms.TextInput(attrs={
            'placeholder': 'شماره موبایل بدون صفر اول'
        })
    )


class verify_otp_form(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label='کد تأیید',
        widget=forms.TextInput(attrs={
            'placeholder': '******',
            'autocomplete': 'off'
        })
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        fields = ['name', 'image', 'bio']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'نام و نام خانوادگی'}),
            'bio': forms.Textarea(attrs={'placeholder': 'درباره خودتان بنویسید...'}),
        }


class CreateTweetForm(forms.ModelForm):
    class Meta:
        model = models.Tweets
        fields = ['content', 'tweet_type', 'image', 'voice', 'video', 'parent']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'چه خبر؟',
                'rows': 4,
                'id': 'tweet-content'
            }),
            'tweet_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'tweet-type'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'tweet-image'
            }),
            'voice': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*',
                'id': 'tweet-voice'
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*',
                'id': 'tweet-video'
            }),
            'parent': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
        self.fields['image'].required = False
        self.fields['voice'].required = False
        self.fields['video'].required = False
        self.fields['tweet_type'].required = False

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '').strip()
        tweet_type = cleaned_data.get('tweet_type', 'text')
        image = cleaned_data.get('image')
        voice = cleaned_data.get('voice')
        video = cleaned_data.get('video')

        if not tweet_type:
            if image:
                tweet_type = 'image'
            elif video:
                tweet_type = 'video'
            elif voice:
                tweet_type = 'voice'
            else:
                tweet_type = 'text'
            cleaned_data['tweet_type'] = tweet_type

        if tweet_type == 'text' and not content:
            raise forms.ValidationError('متن توییت نمی‌تواند خالی باشد')

        if not content and not image and not voice and not video:
            raise forms.ValidationError('حداقل یکی از موارد متن، تصویر، ویس یا ویدیو را وارد کنید')

        return cleaned_data