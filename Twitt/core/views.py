import uuid
import random
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from . import forms
from django.db.models import Q, Count, Prefetch
from . import models
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
import random
import string
import time
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.paginator import Paginator
from django import template
from django.contrib.auth.models import User
from . import sms_service

register = template.Library()

logger = logging.getLogger(__name__)


def request_otp_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        form = forms.register_otp_form(request.POST)

        if form.is_valid():
            phone = form.cleaned_data['phone']

            otp, created = models.OTP.objects.get_or_create(phone=phone)

            otp.code = str(random.randint(100000, 999999))

            otp.created_at = timezone.now()

            otp.save()

            logger.info(f"OTP for {phone}: {otp.code}")

            # Send SMS
            try:
                print("در حال ارسال SMS...")
                result = sms_service.send_sms(phone, otp.code)
                print(f"SMS ارسال شد! نتیجه: {result}")
            except Exception as e:
                print(f"خطای SMS: {e}")
                import traceback
                traceback.print_exc()

            return redirect('verify_otp', phone=phone)
        else:
            return render(request, 'auth/signup_phone.html', {'form': form})

    return render(request, 'auth/signup_phone.html', {'form': forms.register_otp_form()})


def verify_otp_view(request, phone):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        form = forms.verify_otp_form(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                otp = models.OTP.objects.get(phone=phone, code=code)
                if otp.created_at < timezone.now() - timedelta(minutes=2):
                    otp.delete()
                    form.add_error('code', 'کد منقضی شده است.')
                    return render(request, 'auth/verify_otp.html', {'form': form, 'phone': phone})
                otp.delete()

                user = User.objects.filter(username=phone).first()

                if user:
                    profile = models.Profile.objects.filter(user=user).first()
                    if profile and profile.name:
                        login(request, user)
                        return redirect('home')
                    else:
                        login(request, user)
                        return redirect('setup_profile')
                else:
                    user = User.objects.create_user(username=phone)

                    existing_profile = models.Profile.objects.filter(phone=phone).first()

                    if existing_profile:
                        existing_profile.user = user
                        existing_profile.save()
                        profile = existing_profile
                    else:
                        profile = models.Profile.objects.create(
                            user=user,
                            phone=phone,
                            name=''
                        )

                    login(request, user)
                    return redirect('setup_profile')

            except models.OTP.DoesNotExist:
                form.add_error('code', 'کد تایید نادرست است.')
                return render(request, 'auth/verify_otp.html', {'form': form, 'phone': phone})
        return render(request, 'auth/verify_otp.html', {'form': form, 'phone': phone})
    return render(request, 'auth/verify_otp.html', {
        'form': forms.verify_otp_form(),
        'phone': phone
    })


@login_required
def setup_profile(request):
    profile = models.Profile.objects.filter(user=request.user).first()

    if not profile:
        profile = models.Profile(
            user=request.user,
            phone=request.user.username,
            name=''
        )

    if profile and profile.name:
        return redirect('profile')

    if request.method == 'POST':
        form = forms.ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user

            if not profile.phone:
                profile.phone = request.user.username

            if models.Profile.objects.exclude(user=request.user).filter(phone=profile.phone).exists():
                messages.error(request, 'این شماره تلفن قبلاً استفاده شده است')
                return render(request, 'auth/setup_profile.html', {'form': form})

            profile.save()
            return redirect('profile')
    else:
        form = forms.ProfileForm(instance=profile)

    return render(request, 'auth/setup_profile.html', {'form': form})


@login_required
def profile_view(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user

    profile = get_object_or_404(models.Profile, user=profile_user)

    active_tab = request.GET.get('tab', 'posts')

    if active_tab == 'posts':
        tweets = models.Tweets.objects.filter(
            user=profile_user,
            parent__isnull=True
        )
    elif active_tab == 'replies':
        tweets = models.Tweets.objects.filter(
            user=profile_user,
            parent__isnull=False
        )
    elif active_tab == 'media':
        tweets = models.Tweets.objects.filter(
            user=profile_user
        ).filter(
            models.Q(image__isnull=False) |
            models.Q(video__isnull=False)
        )
    elif active_tab == 'likes':
        liked_tweets = models.Like.objects.filter(
            user=profile_user
        ).values_list('tweet_id', flat=True)
        tweets = models.Tweets.objects.filter(
            id__in=liked_tweets
        )
    else:
        tweets = models.Tweets.objects.filter(
            user=profile_user,
            parent__isnull=True
        )

    tweets = tweets.select_related(
        'user',
        'user__profile'
    ).prefetch_related(
        'likes',
        'comments',
        'comments__user',
        'comments__user__profile'
    ).annotate(
        likes_count_annotate=Count('likes', distinct=True),
        comments_count_annotate=Count('comments', distinct=True)
    ).order_by('-created_at')

    tweets_count = tweets.count()

    tweet_list = []
    for tweet in tweets:
        user_liked = models.Like.objects.filter(
            user=request.user,
            tweet=tweet
        ).exists()

        comments = tweet.comments.all()[:3]
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at,
                'user': {
                    'username': comment.user.username,
                    'name': comment.user.get_full_name() or comment.user.username,
                    'profile_image': comment.user.profile.image.url if hasattr(comment.user,
                                                                               'profile') and comment.user.profile.image else None,
                }
            })

        tweet_data = {
            'id': tweet.id,
            'content': tweet.content,
            'image': tweet.image,
            'video': tweet.video,
            'voice': tweet.voice,
            'tweet_type': tweet.tweet_type,
            'created_at': tweet.created_at,
            'user': tweet.user,
            'author': {
                'username': tweet.user.username,
                'name': tweet.user.get_full_name() or tweet.user.username,
                'profile_image': tweet.user.profile.image.url if hasattr(tweet.user,
                                                                         'profile') and tweet.user.profile.image else None,
            },
            'user_name': tweet.user.get_full_name() or tweet.user.username,
            'likes_count': tweet.likes_count_annotate,
            'comments_count': tweet.comments_count_annotate,
            'user_liked': user_liked,
            'comments': comments_data,
        }
        tweet_list.append(tweet_data)

    try:
        followers_count = models.Follow.objects.filter(
            following=profile_user
        ).count()

        following_count = models.Follow.objects.filter(
            follower=profile_user
        ).count()
    except:
        followers_count = 0
        following_count = 0

    is_following = False
    try:
        if request.user != profile_user:
            is_following = models.Follow.objects.filter(
                follower=request.user,
                following=profile_user
            ).exists()
    except:
        is_following = False

    # trends = get_trends()

    context = {
        'profile': profile,
        'profile_user': profile_user,
        'tweets': tweet_list,
        'tweets_count': tweets_count,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following,
        'active_tab': active_tab,
    }

    return render(request, 'profile/profile.html', context)


@login_required
def edit_profile_view(request):
    profile = get_object_or_404(models.Profile, user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        bio = request.POST.get('bio', '').strip()
        phone = request.POST.get('phone', '').strip()
        image = request.FILES.get('image')

        if not name:
            messages.error(request, 'نام نمی‌تواند خالی باشد')
            return render(request, 'profile/edit_profile.html', {'profile': profile})

        # چک کردن تکراری بودن name (به جای phone)
        if models.Profile.objects.exclude(user=request.user).filter(name=name).exists():
            messages.error(request, 'این نام قبلاً استفاده شده است')
            return render(request, 'profile/edit_profile.html', {'profile': profile})

        profile.name = name
        profile.bio = bio
        profile.phone = phone  # دیگه چک نمیشه که تکراری باشه

        if image:
            profile.image = image

        profile.save()
        messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد')
        return redirect('profile')

    context = {
        'profile': profile,
    }
    return render(request, 'profile/edit_profile.html', context)


@login_required
def delete_account_request(request):
    if request.method == 'POST':
        code = ''.join(random.choices(string.digits, k=6))
        request.session['delete_account_code'] = code
        request.session['delete_account_expires'] = str(time.time() + 300)

        print(f"🔐 کد تأیید حذف حساب: {code}")

        logger.info(f"کد تأیید حذف حساب برای کاربر {request.user.username}: {code}")

        messages.success(request, f'کد تأیید: {code} (برای تست نمایش داده شد)')

        return render(request, 'home/confirm_delete.html')


@login_required
def confirm_delete_account(request):
    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip()
        stored_code = request.session.get('delete_account_code')
        expires = request.session.get('delete_account_expires')

        if not stored_code or not expires:
            messages.error(request, 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')
            return redirect('delete_account_request')

        if float(expires) < time.time():
            messages.error(request, 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')
            return redirect('delete_account_request')

        if entered_code != stored_code:
            messages.error(request, 'کد وارد شده اشتباه است.')
            return render(request, 'home/confirm_delete.html')

        user = request.user
        logout(request)
        user.delete()

        messages.success(request, 'حساب کاربری شما با موفقیت حذف شد.')
        return redirect('home')

    return redirect('delete_account_request')



def home(request):
    tweets_qs = models.Tweets.objects.filter(parent__isnull=True).select_related(
        'user', 'user__profile'
    ).annotate(
        likes_count_annotate=Count('likes', distinct=True),
        comments_count_annotate=Count('comments', distinct=True)
    ).order_by('-created_at')[:20]

    comments_qs = models.Comment.objects.select_related(
        'user', 'user__profile'
    ).order_by('-created_at')

    tweets = tweets_qs.prefetch_related(
        Prefetch('comments', queryset=comments_qs[:3], to_attr='latest_comments')
    )

    user_liked_tweets = set()
    if request.user.is_authenticated:
        user_liked_tweets = set(
            models.Like.objects.filter(
                user=request.user,
                tweet__in=tweets
            ).values_list('tweet_id', flat=True)
        )

    tweet_list = []
    for tweet in tweets:
        user_profile = getattr(tweet.user, 'profile', None)
        if user_profile and user_profile.name:
            user_display_name = user_profile.name
        else:
            user_display_name = tweet.user.username

        comments_data = []
        for comment in getattr(tweet, 'latest_comments', []):
            comment_user_profile = getattr(comment.user, 'profile', None)
            comment_display_name = comment_user_profile.name if comment_user_profile and comment_user_profile.name else comment.user.username
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'user': comment.user,
                'username': comment.user.username,
                'user_name': comment_display_name,
                'created_at': comment.created_at,
            })

        tweet_list.append({
            'id': tweet.id,
            'content': tweet.content,
            'image': tweet.image,
            'video': tweet.video,
            'voice': tweet.voice,
            'tweet_type': tweet.tweet_type,
            'created_at': tweet.created_at,
            'user': tweet.user,
            'user_name': user_display_name,
            'likes_count': tweet.likes_count_annotate,
            'comments_count': tweet.comments_count_annotate,
            'user_liked': tweet.id in user_liked_tweets,
            'comments': comments_data,
            # برای راحتی در تمپلیت می‌توانید متد مجازی هم اضافه کنید:
            # 'get_user_display_name': lambda: user_display_name
        })

    return render(request, 'home/home.html', {
        'tweets': tweet_list,
    })


@login_required
def create_tweet(request):
    parent_id = request.GET.get('parent_id') or request.POST.get('parent')
    parent = None
    if parent_id:
        parent = get_object_or_404(models.Tweets, id=parent_id)

    if request.method == 'POST':
        form = forms.CreateTweetForm(request.POST, request.FILES)

        if form.is_valid():
            tweet = form.save(commit=False)
            tweet.user = request.user

            if tweet.image:
                tweet.tweet_type = 'image'
            elif tweet.voice:
                tweet.tweet_type = 'voice'
            elif tweet.video:
                tweet.tweet_type = 'video'
            else:
                tweet.tweet_type = 'text'

            if parent:
                tweet.parent = parent
                tweet.tweet_type = parent.tweet_type

            tweet.save()

            messages.success(request, 'توییت شما با موفقیت منتشر شد!')

            if parent:
                return redirect('tweet_detail', tweet_id=parent.id)

            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = forms.CreateTweetForm(initial={'parent': parent_id})

    context = {
        'form': form,
        'parent': parent,
    }
    return render(request, 'home/home.html', context)


@login_required
def tweet_detail(request, tweet_id):
    tweet = get_object_or_404(
        models.Tweets.objects.select_related('user', 'user__profile'),
        id=tweet_id
    )

    tweet.views_count += 1
    tweet.save(update_fields=['views_count'])

    replies = models.Tweets.objects.filter(parent=tweet).select_related(
        'user', 'user__profile'
    ).prefetch_related('likes')

    user_liked = models.Like.objects.filter(user=request.user, tweet=tweet).exists()

    context = {
        'tweet': tweet,
        'replies': replies,
        'user_liked': user_liked,
    }
    return render(request, 'home/tweet_detail.html', context)


@login_required
def delete_tweet(request, tweet_id):
    tweet = get_object_or_404(models.Tweets, id=tweet_id, user=request.user)

    if request.method == 'POST':
        if tweet.image:
            tweet.image.delete()
        if tweet.voice:
            tweet.voice.delete()
        if tweet.video:
            tweet.video.delete()

        tweet.delete()
        messages.success(request, 'توییت حذف شد')
        return redirect('home')

    return render(request, 'home/home.html', {'tweet': tweet})


@login_required
def create_reply(request, tweet_id):
    if request.method == 'POST':
        parent_tweet = get_object_or_404(models.Tweets, id=tweet_id)
        content = request.POST.get('content').strip()

        if not content:
            messages.error(request, 'متن ریپلای نمی‌تواند خالی باشد')
            return redirect('tweet_detail', tweet_id=tweet_id)

        models.Tweets.objects.create(
            user=request.user,
            content=content,
            tweet_type='text',
            parent=parent_tweet,
        )

        parent_tweet.comments_count = parent_tweet.comments.count()
        parent_tweet.save()
        messages.success(request, 'ریپلای ارسال شد')

        return redirect('tweet_detail', tweet_id=tweet_id)

    return redirect('tweet_detail')


@login_required
def delete_reply(request, tweet_id):
    if request.method == 'POST':
        tweet = get_object_or_404(models.Tweets, id=tweet_id)

        if tweet.user != request.user:
            messages.error(request, 'شما مجاز به حذف این ریپلای نیستید')
            return redirect('tweet_detail', tweet_id=tweet.parent.id)

        parent_tweet_id = tweet.parent.id if tweet.parent else None
        tweet.delete()

        messages.success(request, 'ریپلای حذف شد')

        if parent_tweet_id:
            return redirect('tweet_detail', tweet_id=parent_tweet_id)
        return redirect('home')

    return redirect('home')


@login_required
@require_POST
def like_tweet(request, tweet_id):
    try:
        tweet = get_object_or_404(models.Tweets, id=tweet_id)
        logger.info(f"لایک توییت {tweet_id} توسط کاربر {request.user.username}")

        existing_like = models.Like.objects.filter(user=request.user, tweet=tweet).first()

        if existing_like:
            existing_like.delete()
            liked = False
            logger.info(f"لایک حذف شد برای توییت {tweet_id}")
        else:
            models.Like.objects.create(user=request.user, tweet=tweet)
            liked = True
            logger.info(f"لایک اضافه شد برای توییت {tweet_id}")

        likes_count = tweet.likes.count()
        logger.info(f"تعداد لایک‌های توییت {tweet_id}: {likes_count}")

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'tweet_activities',
            {
                'type': 'tweet_like_update',
                'tweet_id': tweet_id,
                'likes_count': likes_count,
                'liked': liked,
                'username': request.user.username,
            }
        )

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count
        })

    except Exception as e:
        logger.error(f"خطا در لایک کردن: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def add_comment(request, tweet_id):
    try:
        tweet = get_object_or_404(models.Tweets, id=tweet_id)
        content = request.POST.get('content', '').strip()

        if not content:
            return JsonResponse({'success': False, 'error': 'متن کامنت نمی‌تواند خالی باشد'}, status=400)

        comment = models.Comment.objects.create(
            user=request.user,
            tweet=tweet,
            content=content
        )

        tweet.comments_count += 1
        tweet.save(update_fields=['comments_count'])

        user_name = request.user.profile.name if hasattr(request.user,
                                                         'profile') and request.user.profile.name else request.user.username

        return JsonResponse({
            'success': True,
            'comments_count': tweet.comments_count,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'username': request.user.username,
                'user_name': user_name,  # ← اضافه شد
            }
        })

    except Exception as e:
        logger.error(f"خطا در ثبت کامنت: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def delete_comment(request, tweet_id):
    try:
        tweet = get_object_or_404(models.Tweets, id=tweet_id)
        comment_id = request.POST.get('comment_id')

        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'شناسه کامنت وجود ندارد'
            }, status=400)
        comment = get_object_or_404(models.Comment, id=comment_id, tweet=tweet)
        # بررسی مالکیت کامنت
        if comment.user != request.user:
            return JsonResponse({
                'success': False,
                'error': 'شما مجاز به حذف این کامنت نیستید'
            }, status=403)

        comment.delete()

        tweet.comments_count = max(0, tweet.comments_count - 1)
        tweet.save(update_fields=['comments_count'])

        comments_count = tweet.comments.count()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'tweet_activities',
            {
                'type': 'tweet_comment_deleted',
                'tweet_id': tweet_id,
                'comments_count': comments_count,
                'comment_id': comment_id,
                'username': request.user.username,
            }
        )

        return JsonResponse({
            'success': True,
            'comments_count': comments_count,
            'comment_id': comment_id
        })

    except Exception as e:
        logger.error(f"خطا در حذف کامنت: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Search
def search_view(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return render(request, 'search/search.html', {
            'query': '',
            'users': [],
            'tweets': [],
        })

    users = models.User.objects.filter(
        Q(username__istartswith=query) |
        Q(first_name__istartswith=query) |
        Q(last_name__istartswith=query) |
        Q(profile__name__istartswith=query)
    ).select_related('profile').distinct()[:10]

    tweets = models.Tweets.objects.filter(
        Q(content__icontains=query),
        Q(parent__isnull=True)
    ).select_related('user', 'user__profile').prefetch_related(
        'likes'
    ).annotate(
        likes_count_annotate=Count('likes', distinct=True),
        comments_count_annotate=Count('comments', distinct=True)
    ).order_by('-created_at')[:20]

    user_liked_tweets = set()
    if request.user.is_authenticated:
        user_liked_tweets = set(
            models.Like.objects.filter(
                user=request.user,
                tweet__in=tweets
            ).values_list('tweet_id', flat=True)
        )

    tweet_list = []
    for tweet in tweets:
        tweet_data = {
            'id': tweet.id,
            'content': tweet.content,
            'image': tweet.image,
            'video': tweet.video,
            'voice': tweet.voice,
            'tweet_type': tweet.tweet_type,
            'created_at': tweet.created_at,
            'user': tweet.user,
            'user_name': tweet.user.get_full_name() or tweet.user.username,
            'likes_count': tweet.likes_count_annotate,
            'comments_count': tweet.comments_count_annotate,
            'user_liked': tweet.id in user_liked_tweets,
        }
        tweet_list.append(tweet_data)

    return render(request, 'search/search.html', {
        'query': query,
        'users': users,
        'tweets': tweet_list,
    })


# Follow
@login_required
def follow_users(request, user_id):
    logger.error(f"DEBUG: follow_users called with user_id={user_id}")
    logger.error(f"DEBUG: request.user={request.user}, request.user.id={request.user.id}")

    user_to_follow = get_object_or_404(User, id=user_id)
    logger.error(f"DEBUG: user_to_follow={user_to_follow}, id={user_to_follow.id}")

    # ✅ اینجا حتماً == بذار!
    if request.user == user_to_follow:  # <-- دو تا = !
        logger.error("DEBUG: Same user error")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'شما نمی‌توانید خودتان را فالو کنید'}, status=400)
        messages.error(request, 'شما نمی‌توانید خودتان را فالو کنید')
        return redirect('profile', username=user_to_follow.username)

    # چک کردن آیا قبلاً فالو کرده
    if models.Follow.objects.filter(follower=request.user, following=user_to_follow).exists():
        logger.error("DEBUG: Already following")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'شما قبلاً این کاربر را فالو کرده‌اید'}, status=400)
        messages.info(request, 'شما قبلاً این کاربر را فالو کرده‌اید')
        return redirect('profile', username=user_to_follow.username)

    # ایجاد رابطه
    logger.error("DEBUG: Creating follow relationship")
    models.Follow.objects.create(follower=request.user, following=user_to_follow)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        followers_count = models.Follow.objects.filter(following=user_to_follow).count()
        return JsonResponse({
            'success': True,
            'message': f'شما کاربر {user_to_follow.username} را فالو کردید',
            'followers_count': followers_count,
            'is_following': True
        })

    messages.success(request, f'شما کاربر {user_to_follow.username} را فالو کردید')
    return redirect('profile', username=user_to_follow.username)


@login_required
def unfollow_users(request, user_id):
    user_to_unfollow = get_object_or_404(User, id=user_id)

    # ✅ == اضافه شد
    if request.user == user_to_unfollow:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'شما نمی‌توانید خودتان را آنفالو کنید'}, status=400)
        messages.error(request, 'شما نمی‌توانید خودتان را آنفالو کنید')
        return redirect('profile', username=user_to_unfollow.username)

    deleted_count, _ = models.Follow.objects.filter(
        follower=request.user,
        following=user_to_unfollow
    ).delete()

    if deleted_count == 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'شما این کاربر را فالو نکرده‌اید'}, status=400)
        messages.info(request, 'شما این کاربر را فالو نکرده‌اید')
        return redirect('profile', username=user_to_unfollow.username)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        followers_count = models.Follow.objects.filter(following=user_to_unfollow).count()
        return JsonResponse({
            'success': True,
            'message': f'شما کاربر {user_to_unfollow.username} را آنفالو کردید',
            'followers_count': followers_count,
            'is_following': False
        })

    messages.success(request, f'شما کاربر {user_to_unfollow.username} را آنفالو کردید')
    return redirect('profile', username=user_to_unfollow.username)


@login_required
def followers_list(request, username):
    user = get_object_or_404(models.User, username=username)
    followers = models.Follow.objects.filter(
        following=user
    ).select_related(
        'follower',
        'follower__profile'
    ).prefetch_related(
        'follower__profile'
    )

    paginator = Paginator(followers, 20)
    page_number = request.GET.get('page')
    followers_page = paginator.get_page(page_number)

    context = {
        'profile_user': user,
        'followers': followers_page,
        'type': 'followers',
    }
    return render(request, 'followers_list.html', context)


@login_required
def following_list(request, username):
    user = get_object_or_404(models.User, username=username)
    following = models.Follow.objects.filter(
        follower=user
    ).select_related(
        'following',
        'following__profile'
    ).prefetch_related(
        'following__profile'
    )
    paginator = Paginator(following, 20)
    page_number = request.GET.get('page')
    following_page = paginator.get_page(page_number)

    context = {
        'profile_user': user,
        'following': following_page,
        'type': 'following',
    }
    return render(request, 'profile/followers_list.html', context)


@register.filter
def is_following(user, current_user):
    if not current_user.is_authenticated or user == current_user:
        return False

    return models.Follow.objects.filter(follower=current_user, following=user).exists()


@login_required
def toggle_follow(request, username):
    user = get_object_or_404(User, username=username)

    if request.user == user:
        return JsonResponse({'error': 'عملیات مجاز نیست'}, status=400)

    if request.method == 'POST':
        follow_relation = models.Follow.objects.filter(
            follower=request.user,
            following=user
        )

        if follow_relation.exists():
            follow_relation.delete()
            is_following = False
            message = 'آنفالو شدید'
        else:
            models.Follow.objects.create(
                follower=request.user,
                following=user
            )
            is_following = True
            message = 'فالو شدید'

        followers_count = models.Follow.objects.filter(following=user).count()
        following_count = models.Follow.objects.filter(follower=user).count()

        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': is_following,
            'followers_count': followers_count,
            'following_count': following_count,
        })

    return JsonResponse({'error': 'متد مجاز نیست'}, status=405)


def logout_view(request):
    if request.method == 'POST':
        auth_logout(request)
        return redirect('request_otp')

    auth_logout(request)
    return redirect('request_otp')
