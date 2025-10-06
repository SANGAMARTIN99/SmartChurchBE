from django.contrib import admin
from .models import OfferingCard, CardAssignment, OfferingEntry, SecretaryTask, MemberRequest, ActivityLog


@admin.register(OfferingCard)
class OfferingCardAdmin(admin.ModelAdmin):
    list_display = ("code", "street", "number", "is_taken", "assigned_to", "assigned_at")
    list_filter = ("street", "is_taken")
    search_fields = ("code",)


@admin.register(CardAssignment)
class CardAssignmentAdmin(admin.ModelAdmin):
    list_display = ("card", "full_name", "phone_number", "year", "active")
    list_filter = ("year", "active")
    search_fields = ("card__code", "full_name", "phone_number")


@admin.register(OfferingEntry)
class OfferingEntryAdmin(admin.ModelAdmin):
    list_display = ("card", "entry_type", "amount", "date")
    list_filter = ("entry_type", "date")
    search_fields = ("card__code",)


admin.site.register(SecretaryTask)
admin.site.register(MemberRequest)
admin.site.register(ActivityLog)
