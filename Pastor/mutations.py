import graphene
from graphene import relay
from graphene import ObjectType, Field, Boolean, String
from .inputs import EventInput, PrayerRequestInput, UpdatePrayerRequestStatusInput, DevotionalInput , AnnouncementInput, PrayerReplyInput, MarkPrayerInput
from .outputs import Event, PrayerRequest, Devotional, DevotionalAuthor , AnnouncementType , AnnouncementResponse, PrayerReply as PrayerReplyType
from churchMember.models import Event as EventModel, PrayerRequest as PrayerRequestModel, Member as MemberModel, DailyDevotional , Announcement, DevotionalInteraction, PrayerReply
from graphql import GraphQLError
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)

class CreateEvent(graphene.Mutation):
    event = Field(Event)

    class Arguments:
        input = EventInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.role != 'PASTOR':
            raise Exception("Only pastors can create events")

        event = EventModel(
            title=input.title,
            description=input.description or "",
            event_date=input.event_date,
            event_time=input.event_time,
            location=input.location or "",
            created_by=user
        )
        event.save()

        return CreateEvent(
            event=Event(
                id=str(event.id),
                title=event.title,
                date=event.event_date.strftime("%Y-%m-%d"),
                time=event.event_time.strftime("%H:%M"),
                location=event.location,
                description=event.description
            )
        )

class DeleteEvent(graphene.Mutation):
    success = Boolean()

    class Arguments:
        id = String(required=True)

    def mutate(self, info, id):
        user = info.context.user
        if not user.is_authenticated or user.role != 'PASTOR':
            raise Exception("Only pastors can delete events")

        try:
            event = EventModel.objects.get(id=id)
            event.delete()
            return DeleteEvent(success=True)
        except EventModel.DoesNotExist:
            raise Exception("Event not found")

class CreatePrayerRequest(graphene.Mutation):
    prayer_request = Field(PrayerRequest)

    class Arguments:
        input = PrayerRequestInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated :
            raise Exception("User Is Not Authenticated")

        member = MemberModel.objects.get(id=input.member_id)
        prayer = PrayerRequestModel(
            member=member,
            request=input.request,
            is_public=input.is_public,
            status='PENDING'
        )
        prayer.save()

        return CreatePrayerRequest(
            prayer_request=PrayerRequest(
                id=str(prayer.id),
                member=prayer.member.full_name,
                request=prayer.request,
                date=prayer.created_at.strftime("%Y-%m-%d"),
                status=prayer.status
            )
        )

class UpdatePrayerRequestStatus(graphene.Mutation):
    prayer_request = Field(PrayerRequest)

    class Arguments:
        input = UpdatePrayerRequestStatusInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.role != 'PASTOR':
            raise Exception("Only pastors can update prayer request status")

        try:
            prayer = PrayerRequestModel.objects.get(id=input.id)
            prayer.status = input.status
            prayer.updated_at = timezone.now()
            prayer.save()
            return UpdatePrayerRequestStatus(
                prayer_request=PrayerRequest(
                    id=str(prayer.id),
                    member=prayer.member.full_name,
                    request=prayer.request,
                    date=prayer.created_at.strftime("%Y-%m-%d"),
                    status=prayer.status
                )
            )
        except PrayerRequestModel.DoesNotExist:
            raise Exception("Prayer request not found")


def _serialize_prayer(prayer):
    replies = [
        PrayerReplyType(
            responder=rep.responder.full_name if rep.responder else 'Pastoral Team',
            message=rep.message,
            date=rep.created_at.strftime("%Y-%m-%d")
        )
        for rep in PrayerReply.objects.filter(prayer=prayer).order_by('created_at')
    ]
    return PrayerRequest(
        id=str(prayer.id),
        member=prayer.member.full_name,
        request=prayer.request,
        date=prayer.created_at.strftime("%Y-%m-%d"),
        status=prayer.status,
        replies=replies,
    )


class CreatePrayerReply(graphene.Mutation):
    prayer_request = Field(PrayerRequest)

    class Arguments:
        input = PrayerReplyInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.role not in ['PASTOR', 'ASSISTANT_PASTOR', 'EVANGELIST']:
            raise Exception("Only pastoral staff can reply to prayers")

        try:
            prayer = PrayerRequestModel.objects.get(id=input.prayer_id)
        except PrayerRequestModel.DoesNotExist:
            raise Exception("Prayer request not found")

        PrayerReply.objects.create(prayer=prayer, responder=user, message=input.message)
        # Auto-mark as PRAYED if it was pending
        if prayer.status == 'PENDING':
            prayer.status = 'PRAYED'
            prayer.save(update_fields=['status'])

        return CreatePrayerReply(prayer_request=_serialize_prayer(prayer))


class MarkPrayerAsPrayed(graphene.Mutation):
    prayer_request = Field(PrayerRequest)

    class Arguments:
        input = MarkPrayerInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.role not in ['PASTOR', 'ASSISTANT_PASTOR', 'EVANGELIST']:
            raise Exception("Only pastoral staff can update prayer status to PRAYED")
        try:
            prayer = PrayerRequestModel.objects.get(id=input.id)
        except PrayerRequestModel.DoesNotExist:
            raise Exception("Prayer request not found")
        if prayer.status != 'PRAYED':
            prayer.status = 'PRAYED'
            prayer.updated_at = timezone.now()
            prayer.save()
        return MarkPrayerAsPrayed(prayer_request=_serialize_prayer(prayer))


class MemberMarkPrayerAnswered(graphene.Mutation):
    prayer_request = Field(PrayerRequest)

    class Arguments:
        input = MarkPrayerInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        try:
            prayer = PrayerRequestModel.objects.get(id=input.id)
        except PrayerRequestModel.DoesNotExist:
            raise Exception("Prayer request not found")
        # Only the owner can mark as answered
        if prayer.member_id != user.id:
            raise Exception("You can only mark your own prayer as answered")
        if prayer.status != 'ANSWERED':
            prayer.status = 'ANSWERED'
            prayer.updated_at = timezone.now()
            prayer.save()
        return MemberMarkPrayerAnswered(prayer_request=_serialize_prayer(prayer))

class CreateDevotional(graphene.Mutation):
    devotional = Field(Devotional)

    class Arguments:
        input = DevotionalInput(required=True)

    def mutate(self, info, input):
        user = info.context.user
        logger.info(f"Attempting to create devotional with input: {input}")
        if not user.is_authenticated:
            logger.error("User is not authenticated")
            raise Exception("User must be authenticated")
        if user.role != 'PASTOR':
            logger.error(f"User role {user.role} is not PASTOR")
            raise Exception("Only pastors can create devotionals")

        try:
            devotional = DailyDevotional(
                title=input.title,
                scripture=input.scripture,
                content=input.content,
                published_at=input.published_at,
                author=user,
                image_url=input.image_url or "",
                audio_url=input.audio_url or "",
                video_url=input.video_url or ""
            )
            devotional.save()
            logger.info(f"Devotional saved successfully: {devotional.id}")

            return CreateDevotional(
                devotional=Devotional(
                    id=str(devotional.id),
                    title=devotional.title,
                    content=devotional.content,
                    scripture=devotional.scripture,
                    published_at=devotional.published_at.strftime("%Y-%m-%d"),
                    author=DevotionalAuthor(full_name=user.full_name),
                    image_url=devotional.image_url,
                    audio_url=devotional.audio_url,
                    video_url=devotional.video_url
                )
            )
        except Exception as e:
            logger.error(f"Error saving devotional: {str(e)}")
            raise Exception(f"Failed to save devotional: {str(e)}")

class UpdateDevotional(graphene.Mutation):
    devotional = Field(Devotional)

    class Arguments:
        id = String(required=True)
        input = DevotionalInput(required=True)

    def mutate(self, info, id, input):
        user = info.context.user
        if not user.is_authenticated or user.role != 'PASTOR':
            raise Exception("Only pastors can update devotionals")

        try:
            devotional = DailyDevotional.objects.get(id=id)
            devotional.title = input.title
            devotional.scripture = input.scripture
            devotional.content = input.content
            devotional.published_at = input.published_at
            devotional.image_url = input.image_url or devotional.image_url
            devotional.audio_url = input.audio_url or devotional.audio_url
            devotional.video_url = input.video_url or devotional.video_url
            devotional.updated_at = timezone.now()
            devotional.save()

            return UpdateDevotional(
                devotional=Devotional(
                    id=str(devotional.id),
                    title=devotional.title,
                    content=devotional.content,
                    scripture=devotional.scripture,
                    published_at=devotional.published_at.strftime("%Y-%m-%d"),
                    author=DevotionalAuthor(full_name=devotional.author.full_name if devotional.author else "Anonymous"),
                    image_url=devotional.image_url,
                    audio_url=devotional.audio_url,
                    video_url=devotional.video_url
                )
            )
        except DailyDevotional.DoesNotExist:
            raise Exception("Devotional not found")


class ToggleBookmark(graphene.Mutation):
    bookmarked = graphene.Boolean()

    class Arguments:
        devotional_id = graphene.String(required=True)

    def mutate(self, info, devotional_id):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required")
        try:
            devotional = DailyDevotional.objects.get(id=devotional_id)
        except DailyDevotional.DoesNotExist:
            raise GraphQLError("Devotional not found")
        interaction, _ = DevotionalInteraction.objects.get_or_create(member=user, devotional=devotional)
        interaction.bookmarked = not interaction.bookmarked
        interaction.save()
        return ToggleBookmark(bookmarked=interaction.bookmarked)


class ToggleAmen(graphene.Mutation):
    amened = graphene.Boolean()
    amen_count = graphene.Int()

    class Arguments:
        devotional_id = graphene.String(required=True)

    def mutate(self, info, devotional_id):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required")
        try:
            devotional = DailyDevotional.objects.get(id=devotional_id)
        except DailyDevotional.DoesNotExist:
            raise GraphQLError("Devotional not found")
        interaction, _ = DevotionalInteraction.objects.get_or_create(member=user, devotional=devotional)
        interaction.amened = not interaction.amened
        interaction.save()
        count = DevotionalInteraction.objects.filter(devotional=devotional, amened=True).count()
        return ToggleAmen(amened=interaction.amened, amen_count=count)


class SaveJournal(graphene.Mutation):
    journal = graphene.String()

    class Arguments:
        devotional_id = graphene.String(required=True)
        text = graphene.String(required=True)

    def mutate(self, info, devotional_id, text):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required")
        try:
            devotional = DailyDevotional.objects.get(id=devotional_id)
        except DailyDevotional.DoesNotExist:
            raise GraphQLError("Devotional not found")
        interaction, _ = DevotionalInteraction.objects.get_or_create(member=user, devotional=devotional)
        interaction.journal = text
        interaction.save()
        return SaveJournal(journal=interaction.journal)
class DeleteDevotional(graphene.Mutation):
    success = Boolean()

    class Arguments:
        id = String(required=True)

    def mutate(self, info, id):
        user = info.context.user
        if not user.is_authenticated or user.role != 'PASTOR':
            raise Exception("Only pastors can delete devotionals")

        try:
            devotional = DailyDevotional.objects.get(id=id)
            devotional.delete()
            return DeleteDevotional(success=True)
        except DailyDevotional.DoesNotExist:
            raise Exception("Devotional not found")
        
        
class CreateAnnouncement(relay.ClientIDMutation):
    class Input:
        input = AnnouncementInput(required=True)  # Use the defined AnnouncementInput

    announcement = graphene.Field(AnnouncementType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, input=None):
        try:
            announcement_data = input or {}
            announcement = Announcement.objects.create(
                title=announcement_data.get('title'),
                content=announcement_data.get('content'),
                category=announcement_data.get('category'),
                is_pinned=announcement_data.get('is_pinned', False),
                location=announcement_data.get('location'),
                created_by=info.context.user,
                **({} if not announcement_data.get('target_group') else {'target_group_id': announcement_data['target_group']}),
                **({} if not announcement_data.get('event_date') else {'event_date': announcement_data['event_date']}),
                **({} if not announcement_data.get('event_time') else {'event_time': announcement_data['event_time']}),
            )
            return CreateAnnouncement(announcement=announcement, success=True, message='Announcement created successfully.')
        except Exception as e:
            return CreateAnnouncement(announcement=None, success=False, message=str(e))

class UpdateAnnouncement(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        input = AnnouncementInput(required=True)  # Use the defined AnnouncementInput

    announcement = graphene.Field(AnnouncementType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, input=None):
        try:
            announcement = Announcement.objects.get(pk=id)
            announcement_data = input or {}
            for key, value in announcement_data.items():
                if value is not None and key != 'id':
                    setattr(announcement, key, value)
            announcement.save()
            return UpdateAnnouncement(announcement=announcement, success=True, message='Announcement updated successfully.')
        except Announcement.DoesNotExist:
            return UpdateAnnouncement(announcement=None, success=False, message='Announcement not found.')
        except Exception as e:
            return UpdateAnnouncement(announcement=None, success=False, message=str(e))

class DeleteAnnouncement(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            announcement = Announcement.objects.get(pk=input['id'])
            announcement.delete()
            return DeleteAnnouncement(success=True, message='Announcement deleted successfully.')
        except Announcement.DoesNotExist:
            return DeleteAnnouncement(success=False, message='Announcement not found.')
        except Exception as e:
            return DeleteAnnouncement(success=False, message=str(e))

class PastorMutation(ObjectType):
    create_event = CreateEvent.Field()
    delete_event = DeleteEvent.Field()
    create_prayer_request = CreatePrayerRequest.Field()
    update_prayer_request_status = UpdatePrayerRequestStatus.Field()
    create_devotional = CreateDevotional.Field()
    update_devotional = UpdateDevotional.Field()
    delete_devotional = DeleteDevotional.Field()
    create_announcement = CreateAnnouncement.Field()
    update_announcement = UpdateAnnouncement.Field()
    delete_announcement = DeleteAnnouncement.Field()
    toggle_bookmark = ToggleBookmark.Field()
    toggle_amen = ToggleAmen.Field()
    save_journal = SaveJournal.Field()
    create_prayer_reply = CreatePrayerReply.Field()
    mark_prayer_as_prayed = MarkPrayerAsPrayed.Field()
    member_mark_prayer_answered = MemberMarkPrayerAnswered.Field()