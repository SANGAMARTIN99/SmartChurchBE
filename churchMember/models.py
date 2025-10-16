from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from UserAuthentication.models import *
import uuid



class Offering(models.Model):
    OFFERING_TYPES = (
        ('TITHE', 'Tithe'),
        ('SPECIAL_OFFERING', 'Special Offering'),
        ('GENERAL_CONTRIBUTION', 'General Contribution'),
        # Extended to align with Secretary entries
        ('AHADI', 'Ahadi'),
        ('SHUKRANI', 'Shukrani'),
        ('MAJENGO', 'Majengo'),
    )
    MASS_TYPES = (
        ('MAJOR', 'Major'),
        ('MORNING_GLORY', 'Morning Glory'),
        ('EVENING_GLORY', 'Evening Glory'),
        ('SELI', 'SELI'),
    )

    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='offerings')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    offering_type = models.CharField(max_length=50, choices=OFFERING_TYPES)
    mass_type = models.CharField(max_length=50, choices=MASS_TYPES)
    street = models.ForeignKey(Street, on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    attendant = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='attended_offerings')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.offering_type} by {self.member.full_name if self.member else 'Anonymous'}"


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_date = models.DateField()
    event_time = models.TimeField()
    location = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title





class EventRSVP(models.Model):
    RSVP_STATUS = (
        ('CONFIRMED', 'Confirmed'),
        ('DECLINED', 'Declined'),
        ('PENDING', 'Pending'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    rsvp_status = models.CharField(max_length=20, choices=RSVP_STATUS, default='PENDING')
    responded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'member')

    def __str__(self):
        return f"{self.member.full_name} RSVP {self.rsvp_status} for {self.event.title}"


class PrayerRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PRAYED', 'Prayed'),
        ('ANSWERED', 'Answered'),
    )

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    request = models.TextField()
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prayer by {self.member.full_name}"


class PrayerReply(models.Model):
    prayer = models.ForeignKey(PrayerRequest, on_delete=models.CASCADE, related_name='replies')
    responder = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.responder.full_name if self.responder else 'Pastoral Team'} on #{self.prayer_id}"


class DailyDevotional(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    scripture = models.CharField(max_length=255, blank=True)
    audio_url = models.CharField(max_length=255, blank=True)
    video_url = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=255, blank=True)
    author = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class DevotionalInteraction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    devotional = models.ForeignKey(DailyDevotional, on_delete=models.CASCADE)
    bookmarked = models.BooleanField(default=False)
    amened = models.BooleanField(default=False)
    journal = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('member', 'devotional')

    def __str__(self):
        return f"Interaction({self.member.full_name} -> {self.devotional.title})"


class Announcement(models.Model):
    TITLE_MAX_LENGTH = 200
    CONTENT_MAX_LENGTH = 1000

    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    content = models.TextField(max_length=CONTENT_MAX_LENGTH)
    category = models.CharField(
        max_length=50,
        choices=[
            ('events', 'Events'),
            ('services', 'Service Changes'),
            ('community', 'Community News'),
            ('urgent', 'Urgent Updates'),
            ('general', 'General'),
        ],
        default='general'
    )
    is_pinned = models.BooleanField(default=False)
    target_group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(Member, null=True, on_delete=models.SET_NULL, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rsvp_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('ANNOUNCEMENT', 'Announcement'),
        ('REMINDER', 'Reminder'),
        ('PLEDGE_UPDATE', 'Pledge Update'),
        ('GROUP_EVENT', 'Group Event'),
    )
    DELIVERY_METHODS = (
        ('WEB', 'Web'),
        ('SMS', 'SMS'),
    )

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    related_id = models.IntegerField(blank=True, null=True)
    related_type = models.CharField(max_length=50, blank=True)
    is_read = models.BooleanField(default=False)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS, default='WEB')
    sms_status = models.CharField(max_length=50, blank=True)  # e.g., 'sent', 'failed', 'pending'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification_type} for {self.member.full_name}"


class BlogPost(models.Model):
    CATEGORY_CHOICES = (
        ('TESTIMONIES', 'Testimonies'),
        ('PRAYER_REQUESTS', 'Prayer Requests'),
        ('COMMUNITY_EVENTS', 'Community Events'),
    )

    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, blank=True)
    author = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class BlogComment(models.Model):
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.member.full_name if self.member else 'Anonymous'} on {self.blog_post.title}"


