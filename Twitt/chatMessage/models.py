from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receiver')
    message = models.TextField()
    time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='SENT', choices=[
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('SEEN', 'Seen'),
    ])
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.message[:20]}"
