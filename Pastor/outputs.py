import graphene
from graphene_django.types import DjangoObjectType
from graphene import ObjectType, String, Int, Float, Date, Time, List, Field, Boolean
from churchMember.models import Announcement
from UserAuthentication.models import Member, Group  # Assuming these models exist

class DashboardStats(ObjectType):
    total_members = Int()
    active_groups = Int()
    prayer_requests = Int()
    total_offerings = Float()
    weekly_offerings = Float()
    monthly_offerings = Float()
    new_members_this_month = Int()
    new_prayer_requests_today = Int()

class Member(ObjectType):
    id = String()
    full_name = String()
    street = String()
    joined_date = String()
    profile_photo = String()

class Group(ObjectType):
    id = String()
    name = String()

class Event(ObjectType):
    id = String()
    title = String()
    date = String()
    time = String()
    location = String()
    description = String()

class PrayerReply(ObjectType):
    responder = String()
    message = String()
    date = String()

class PrayerRequest(ObjectType):
    id = String()
    member = String()
    request = String()
    date = String()
    status = String()
    replies = List(PrayerReply)

class OfferingStats(ObjectType):
    this_week = Float()
    last_week = Float()
    this_month = Float()
    last_month = Float()
    trend = String()
    
class DevotionalAuthor(ObjectType):
    full_name = String()

class Devotional(ObjectType):
    id = String()
    title = String()
    content = String()
    scripture = String()
    published_at = String()
    author = Field(DevotionalAuthor)
    image_url = String()
    audio_url = String()
    video_url = String()
    amen_count = Int()


class DevotionalInteraction(ObjectType):
    bookmarked = Boolean()
    amened = Boolean()
    journal = String()

class AnnouncementType(DjangoObjectType):
    class Meta:
        model = Announcement
        fields = '__all__'

    created_by_full_name = String()
    target_group_name = String()

    def resolve_created_by_full_name(self, info):
        return self.created_by.full_name if self.created_by else 'Church Office'

    def resolve_target_group_name(self, info):
        return self.target_group.name if self.target_group else None

class AnnouncementResponse(ObjectType):
    success = Boolean()
    message = String()
    announcement = Field(AnnouncementType)

# New types for offerings data
class OfferingRecord(ObjectType):
    id = String()
    date = String()
    member_name = String()
    street = String()
    amount = Float()
    offering_type = String()
    mass_type = String()
    attendant = String()

class MassTypeStat(ObjectType):
    type = String()
    amount = Float()
    percentage = Float()

class OfferingTypeStat(ObjectType):
    type = String()
    amount = Float()
    percentage = Float()

# Street-wise aggregation
class StreetStat(ObjectType):
    name = String()
    total = Float()
    member_count = Int()
    average = Float()
    trend = String()