from django.db import models
from django.conf import settings
from django.utils import timezone
from UserAuthentication.models import Street, Member


def current_year():
    return timezone.now().year


class SecretaryTask(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "low"
        MEDIUM = "MEDIUM", "medium"
        HIGH = "HIGH", "high"
        URGENT = "URGENT", "urgent"

    class Status(models.TextChoices):
        PENDING = "PENDING", "pending"
        IN_PROGRESS = "IN_PROGRESS", "in-progress"
        COMPLETED = "COMPLETED", "completed"
        OVERDUE = "OVERDUE", "overdue"

    class Category(models.TextChoices):
        MEMBERSHIP = "MEMBERSHIP", "membership"
        FINANCE = "FINANCE", "finance"
        EVENTS = "EVENTS", "events"
        COMMUNICATION = "COMMUNICATION", "communication"
        ADMINISTRATION = "ADMINISTRATION", "administration"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="secretary_tasks")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ADMINISTRATION)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.priority})"


class MemberRequest(models.Model):
    class RequestType(models.TextChoices):
        CARD_ISSUE = "CARD_ISSUE", "card-issue"
        PROFILE_UPDATE = "PROFILE_UPDATE", "profile-update"
        GROUP_JOIN = "GROUP_JOIN", "group-join"
        PRAYER_REQUEST = "PRAYER_REQUEST", "prayer-request"
        OTHER = "OTHER", "other"

    class Status(models.TextChoices):
        NEW = "NEW", "new"
        PROCESSING = "PROCESSING", "processing"
        COMPLETED = "COMPLETED", "completed"

    class Urgency(models.TextChoices):
        NORMAL = "NORMAL", "normal"
        URGENT = "URGENT", "urgent"

    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="secretary_requests")
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.NORMAL)
    details = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.member} - {self.request_type}"


class ActivityLog(models.Model):
    class Type(models.TextChoices):
        SUCCESS = "SUCCESS", "success"
        WARNING = "WARNING", "warning"
        INFO = "INFO", "info"

    action = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.INFO)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} ({self.type})"


class OfferingCard(models.Model):
    street = models.ForeignKey(Street, on_delete=models.CASCADE, related_name="offering_cards")
    number = models.PositiveIntegerField()
    code = models.CharField(max_length=16, unique=True, db_index=True)
    is_taken = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_offering_cards")
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("street", "number")
        ordering = ["street__name", "number"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        # Generate code like PR-001 using first two letters of street name
        if self.street and self.number and not self.code:
            name = (self.street.name or "").upper()
            # pick first two alphabetic characters
            prefix = "".join([c for c in name if c.isalpha()][:2])
            self.code = f"{prefix}-{self.number:03d}"
        super().save(*args, **kwargs)


class CardAssignment(models.Model):
    card = models.OneToOneField(OfferingCard, on_delete=models.CASCADE, related_name="assignment")
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="offering_card_assignments")
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    year = models.PositiveIntegerField(default=current_year)
    pledged_ahadi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pledged_shukrani = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pledged_majengo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.card.code} -> {self.full_name} ({self.year})"


class OfferingEntry(models.Model):
    class Type(models.TextChoices):
        AHADI = "AHADI", "Ahadi"
        SHUKRANI = "SHUKRANI", "Shukrani"
        MAJENGO = "MAJENGO", "Majengo"

    card = models.ForeignKey(OfferingCard, on_delete=models.CASCADE, related_name="entries")
    entry_type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card.code} {self.entry_type} {self.amount} on {self.date}"
