import graphene
from graphene import ObjectType, Field, List, Int
from django.utils import timezone
from asgiref.sync import sync_to_async
from datetime import timedelta
from django.db.models import Sum, Count
from .outputs import (
    DashboardStats,
    Member,
    Event,
    PrayerRequest,
    OfferingStats,
    Devotional,
    DevotionalAuthor,
    AnnouncementType,
    OfferingRecord,
    MassTypeStat,
    OfferingTypeStat,
)
from graphql import GraphQLError
from churchMember.models import Member as MemberModel, Group, PrayerRequest as PrayerRequestModel, Offering, Event as EventModel, DailyDevotional, Announcement
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PastorQuery(ObjectType):
    dashboard_stats = Field(DashboardStats)
    recent_members = List(Member)
    upcoming_events = List(Event)
    prayer_requests = List(PrayerRequest)
    offering_stats = Field(OfferingStats)
    devotionals = List(Devotional, limit=Int(default_value=10), offset=Int(default_value=0))
    announcements = List(AnnouncementType)
    recent_offerings = List(OfferingRecord, limit=Int(default_value=10))
    offerings_by_mass = List(MassTypeStat, start=graphene.String(), end=graphene.String())
    offerings_by_type = List(OfferingTypeStat, start=graphene.String(), end=graphene.String())

    def resolve_dashboard_stats(self, info):
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return DashboardStats(
            total_members=MemberModel.objects.count(),
            active_groups=Group.objects.count(),
            prayer_requests=PrayerRequestModel.objects.count(),
            total_offerings=Offering.objects.aggregate(total=Sum('amount'))['total'] or 0,
            weekly_offerings=Offering.objects.filter(
                date__gte=now - timedelta(days=7)
            ).aggregate(total=Sum('amount'))['total'] or 0,
            monthly_offerings=Offering.objects.filter(
                date__gte=this_month_start
            ).aggregate(total=Sum('amount'))['total'] or 0,
            new_members_this_month=MemberModel.objects.filter(
                created_at__gte=this_month_start
            ).count(),
            new_prayer_requests_today=PrayerRequestModel.objects.filter(
                created_at__gte=today_start
            ).count()
        )

    def resolve_recent_members(self, info):
        return [
            Member(
                id=str(member.id),
                full_name=member.full_name,
                street=member.street.name if member.street else "",
                joined_date=member.created_at.strftime("%Y-%m-%d"),
                profile_photo=member.profile_photo or ""
            )
            for member in MemberModel.objects.order_by('-created_at')[:5]
        ]

    def resolve_upcoming_events(self, info):
        now = timezone.now()
        return [
            Event(
                id=str(event.id),
                title=event.title,
                date=event.event_date.strftime("%Y-%m-%d"),
                time=event.event_time.strftime("%H:%M"),
                location=event.location or "",
                description=event.description or ""
            )
            for event in EventModel.objects.filter(event_date__gte=now).order_by('event_date', 'event_time')[:5]
        ]

    def resolve_prayer_requests(self, info):
        return [
            PrayerRequest(
                id=str(prayer.id),
                member=prayer.member.full_name,
                request=prayer.request,
                date=prayer.created_at.strftime("%Y-%m-%d"),
                status=prayer.status
            )
            for prayer in PrayerRequestModel.objects.order_by('-created_at')[:10]
        ]

    def resolve_offering_stats(self, info):
        now = timezone.now()
        this_week_start = now - timedelta(days=now.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        this_week = Offering.objects.filter(
            date__gte=this_week_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        last_week = Offering.objects.filter(
            date__gte=last_week_start, date__lt=this_week_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        this_month = Offering.objects.filter(
            date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        last_month = Offering.objects.filter(
            date__gte=last_month_start, date__lt=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        trend = 'up' if this_week >= last_week else 'down'

        return OfferingStats(
            this_week=this_week,
            last_week=last_week,
            this_month=this_month,
            last_month=last_month,
            trend=trend
        )

    def resolve_recent_offerings(self, info, limit=10):
        qs = Offering.objects.select_related('member', 'street', 'attendant').order_by('-date', '-created_at')[:limit]
        records = []
        for o in qs:
            records.append(
                OfferingRecord(
                    id=str(o.id),
                    date=o.date.strftime('%Y-%m-%d') if o.date else '',
                    member_name=o.member.full_name if o.member else 'Anonymous',
                    street=o.street.name if o.street else '',
                    amount=float(o.amount or 0),
                    offering_type=o.offering_type,
                    mass_type=o.mass_type,
                    attendant=o.attendant.full_name if o.attendant else ''
                )
            )
        return records

    def resolve_offerings_by_mass(self, info, start=None, end=None):
        qs = Offering.objects.all()
        if start:
            try:
                start_dt = datetime.fromisoformat(start).date()
                qs = qs.filter(date__gte=start_dt)
            except Exception:
                pass
        if end:
            try:
                end_dt = datetime.fromisoformat(end).date()
                qs = qs.filter(date__lte=end_dt)
            except Exception:
                pass
        total = qs.aggregate(total=Sum('amount'))['total'] or 0
        agg = qs.values('mass_type').annotate(amount=Sum('amount')).order_by('-amount')
        result = []
        for row in agg:
            amt = float(row['amount'] or 0)
            perc = float((amt / total) * 100) if total else 0.0
            result.append(MassTypeStat(type=row['mass_type'], amount=amt, percentage=perc))
        return result

    def resolve_offerings_by_type(self, info, start=None, end=None):
        qs = Offering.objects.all()
        if start:
            try:
                start_dt = datetime.fromisoformat(start).date()
                qs = qs.filter(date__gte=start_dt)
            except Exception:
                pass
        if end:
            try:
                end_dt = datetime.fromisoformat(end).date()
                qs = qs.filter(date__lte=end_dt)
            except Exception:
                pass
        total = qs.aggregate(total=Sum('amount'))['total'] or 0
        agg = qs.values('offering_type').annotate(amount=Sum('amount')).order_by('-amount')
        result = []
        for row in agg:
            amt = float(row['amount'] or 0)
            perc = float((amt / total) * 100) if total else 0.0
            result.append(OfferingTypeStat(type=row['offering_type'], amount=amt, percentage=perc))
        return result

    def resolve_devotionals(self, info, limit=10, offset=0):
        return [
            Devotional(
                id=str(devotional.id),
                title=devotional.title,
                content=devotional.content,
                scripture=devotional.scripture or "",
                published_at=devotional.published_at.strftime("%Y-%m-%d"),
                author=DevotionalAuthor(
                    full_name=devotional.author.full_name if devotional.author else "Anonymous"
                ),
                image_url=devotional.image_url or "",
                audio_url=devotional.audio_url or "",
                video_url=devotional.video_url or ""
            )
            for devotional in DailyDevotional.objects.order_by('-published_at')[offset:offset+limit]
        ]
    
    def resolve_announcements(self, info):
        # Return all announcements ordered by most recent first
        return Announcement.objects.all().order_by('-created_at')
        



from graphene_django.filter import DjangoFilterConnectionField


class AnnouncementQuery(ObjectType):
    announcements = DjangoFilterConnectionField(AnnouncementType)

    def resolve_announcements(self, info, **kwargs):
        return Announcement.objects.all()

    announcement = Field(AnnouncementType, id=graphene.ID(required=True))

    def resolve_announcement(self, info, id):
        return Announcement.objects.get(pk=id)