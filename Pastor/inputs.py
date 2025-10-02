import graphene
from graphene_django.types import DjangoObjectType

from graphene import InputObjectType, String, Int, Float, Date, Time, Boolean

class EventInput(InputObjectType):
    title = String(required=True)
    description = String()
    event_date = Date(required=True)
    event_time = Time(required=True)
    location = String()
    created_by_id = Int(required=True)

class PrayerRequestInput(InputObjectType):
    request = String(required=True)
    is_public = Boolean(default_value=False)
    member_id = Int(required=True)

class UpdatePrayerRequestStatusInput(InputObjectType):
    id = Int(required=True)
    status = String(required=True)
    
class DevotionalInput(InputObjectType):
    title = String(required=True)
    scripture = String(required=True)
    content = String(required=True)
    published_at = Date(required=True)
    image_url = String()  # Optional image URL
    audio_url = String()  # Optional audio URL
    video_url = String()  # Optional video URL 

class PrayerReplyInput(InputObjectType):
    prayer_id = Int(required=True)
    message = String(required=True)

class MarkPrayerInput(InputObjectType):
    id = Int(required=True)

class AnnouncementInput(graphene.InputObjectType):
    title = graphene.String(required=True)
    content = graphene.String(required=True)
    category = graphene.String(required=True, choices=['events', 'services', 'community', 'urgent', 'general'])
    is_pinned = graphene.Boolean()
    target_group_id = graphene.ID()  # Ensure this matches the model foreign key
    event_date = graphene.Date()
    event_time = graphene.Time()
    location = graphene.String()

class UpdateAnnouncementStatusInput(graphene.InputObjectType):
    class Meta:
        model = 'churchMember.models.Announcement'
        fields = ('is_pinned',)