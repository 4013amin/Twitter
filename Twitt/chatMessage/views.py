from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
import json

from . import models


# Create your views here.
def chat_room(request, username=None):
    if not request.user.is_authenticated:
        return redirect('login')

    sent_messages = models.ChatMessage.objects.filter(sender=request.user).values_list('receiver', flat=True)
    received_messages = models.ChatMessage.objects.filter(receiver=request.user).values_list('sender', flat=True)
    chat_user_ids = set(list(sent_messages) + list(received_messages))

    chat_users = []
    for user_id in chat_user_ids:
        try:
            user = User.objects.get(id=user_id)
            last_msg = models.ChatMessage.objects.filter(
                Q(sender=request.user, receiver=user) |
                Q(sender=user, receiver=request.user)
            ).order_by('-time').first()

            unread_count = models.ChatMessage.objects.filter(
                sender=user,
                receiver=request.user,
                is_read=False
            ).count()

            chat_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'profile': user.profile,
                'last_message': last_msg.message if last_msg else '',
                'last_message_time': last_msg.time if last_msg else None,
                'unread_count': unread_count,
            })
        except User.DoesNotExist:
            continue

    chat_users.sort(key=lambda x: x['last_message_time'] or '', reverse=True)

    selected_user = None
    messages = []

    if username:
        selected_user = get_object_or_404(User, username=username)
        messages = models.ChatMessage.objects.filter(
            Q(sender=request.user, receiver=selected_user) |
            Q(sender=selected_user, receiver=request.user)
        ).order_by('time')

        # علامت‌گذاری پیام‌ها به عنوان خوانده شده
        models.ChatMessage.objects.filter(
            sender=selected_user,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)

    return render(request, 'chat/chat.html', {
        'users': chat_users,
        'selected_user': selected_user,
        'messages': messages
    })


@login_required
@require_POST
def send_message(request):
    data = json.loads(request.body)
    message_text = data.get('message', '').strip()
    receiver_id = data.get('receiver_id')
    reply_to_id = data.get('reply_to_id')  # برای ریپلای

    if not message_text or not receiver_id:
        return JsonResponse({'success': False, 'error': 'داده نامعتبر'})

    try:
        receiver = User.objects.get(id=receiver_id)
        reply_to = None
        if reply_to_id:
            reply_to = models.ChatMessage.objects.get(id=reply_to_id)

        message = models.ChatMessage.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message_text,
            reply_to=reply_to
        )
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'time': message.time.strftime('%H:%M'),
            'reply_to': {
                'id': reply_to.id,
                'message': reply_to.message[:50] if reply_to else None,
                'sender': reply_to.sender.username if reply_to else None,
            } if reply_to else None
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'کاربر یافت نشد'})
    except models.ChatMessage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'پیام ریپلای یافت نشد'})





@login_required
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(models.ChatMessage, id=message_id)
    if message.sender != request.user:
        return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})
    message.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def delete_conversation(request, username):
    other_user = get_object_or_404(User, username=username)
    deleted_count, _ = models.ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).delete()
    return JsonResponse({
        'success': True,
        'deleted_count': deleted_count
    })


@login_required
@require_POST
def delete_message_for_me(request, message_id):
    message = get_object_or_404(
        models.ChatMessage,
        id=message_id,
    )

    if message.sender == request.user:
        message.delete()
    else:

        message.delete()

    return JsonResponse({'success': True})
