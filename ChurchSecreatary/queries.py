import graphene
from graphene import ObjectType, List, Int, String
from django.utils import timezone
from datetime import timedelta

from django.db.models import Sum, Count
from .models import SecretaryTask, MemberRequest as MemberRequestModel, ActivityLog, OfferingCard, CardAssignment, OfferingEntry
from .outputs import (
    SecretaryTaskType,
    MemberRequestType,
    QuickStatType,
    ActivityLogType,
    OfferingCardType,
    AvailableCardNumberType,
    CardsOverviewType,
)


class SecretaryQuery(ObjectType):
    secretary_tasks = List(SecretaryTaskType, time_filter=String(default_value="week"))
    member_requests = List(MemberRequestType, status=String())
    secretary_quick_stats = List(QuickStatType)
    secretary_activity = List(ActivityLogType, limit=Int(default_value=10))
    offering_cards = List(OfferingCardType, street_id=Int(), is_taken=graphene.Boolean(), search=String())
    available_card_numbers = List(AvailableCardNumberType, street_id=Int())
    cards_overview = graphene.Field(CardsOverviewType, street_id=Int())

    def resolve_secretary_tasks(self, info, time_filter="week"):
        qs = SecretaryTask.objects.all().order_by('due_date')
        if time_filter == 'today':
            today = timezone.now().date()
            qs = qs.filter(due_date=today)
        elif time_filter == 'week':
            start = timezone.now().date()
            end = start + timedelta(days=7)
            qs = qs.filter(due_date__gte=start, due_date__lte=end)
        # map to GraphQL type
        results = []
        for t in qs:
            results.append(
                SecretaryTaskType(
                    id=str(t.id),
                    title=t.title,
                    description=t.description or "",
                    priority=t.Priority(t.priority).label,
                    status=t.Status(t.status).label,
                    due_date=t.due_date.strftime('%Y-%m-%d') if t.due_date else "",
                    assigned_to=(t.assigned_to.full_name if getattr(t.assigned_to, 'full_name', None) else (t.assigned_to.get_username() if t.assigned_to else "")),
                    category=t.Category(t.category).label,
                )
            )
        return results

    def resolve_member_requests(self, info, status=None):
        qs = MemberRequestModel.objects.all().order_by('-submitted_at')
        if status:
            # status is provided like 'new'|'processing'|'completed'. Our enum stores uppercase keys.
            status_map = {
                'new': MemberRequestModel.Status.NEW,
                'processing': MemberRequestModel.Status.PROCESSING,
                'completed': MemberRequestModel.Status.COMPLETED,
            }
            enum_val = status_map.get(status.lower())
            if enum_val:
                qs = qs.filter(status=enum_val)
        results = []
        for r in qs:
            results.append(
                MemberRequestType(
                    id=str(r.id),
                    member_name=(r.member.full_name if getattr(r.member, 'full_name', None) else r.member.get_username()),
                    request_type=MemberRequestModel.RequestType(r.request_type).label,
                    status=MemberRequestModel.Status(r.status).label,
                    submitted_date=r.submitted_at.strftime('%Y-%m-%d'),
                    urgency=MemberRequestModel.Urgency(r.urgency).label,
                    details=r.details or "",
                )
            )
        return results

    def resolve_secretary_quick_stats(self, info):
        # Simple initial stats; can be enhanced with real calculations
        total_tasks = SecretaryTask.objects.count()
        pending = SecretaryTask.objects.exclude(status=SecretaryTask.Status.COMPLETED).count()
        urgent = SecretaryTask.objects.filter(priority=SecretaryTask.Priority.URGENT).count()
        new_requests = MemberRequestModel.objects.filter(status=MemberRequestModel.Status.NEW).count()
        return [
            QuickStatType(title='Pending Tasks', value=pending, change=0, trend='up'),
            QuickStatType(title='New Requests', value=new_requests, change=0, trend='down'),
            QuickStatType(title='Total Tasks', value=total_tasks, change=0, trend='up'),
            QuickStatType(title='Urgent Tasks', value=urgent, change=0, trend='up'),
        ]

    def resolve_secretary_activity(self, info, limit=10):
        logs = ActivityLog.objects.order_by('-created_at')[:limit]
        results = []
        for a in logs:
            results.append(
                ActivityLogType(
                    action=a.action,
                    user=(a.user.full_name if getattr(a.user, 'full_name', None) else (a.user.get_username() if a.user else 'System')),
                    time=a.created_at.strftime('%Y-%m-%d %H:%M'),
                    type=ActivityLog.Type(a.type).label.lower(),
                )
            )
        return results

    def resolve_offering_cards(self, info, street_id=None, is_taken=None, search=None):
        qs = OfferingCard.objects.select_related('street', 'assigned_to').all()
        if street_id:
            qs = qs.filter(street_id=street_id)
        if is_taken is not None:
            qs = qs.filter(is_taken=is_taken)
        if search:
            qs = qs.filter(code__icontains=search)

        # Preload assignments
        assignments = {a.card_id: a for a in CardAssignment.objects.filter(card_id__in=qs.values_list('id', flat=True))}
        # Precompute sums
        sums = (
            OfferingEntry.objects.filter(card_id__in=qs.values_list('id', flat=True))
            .values('card_id', 'entry_type')
            .annotate(total=Sum('amount'))
        )
        total_map = {}
        for row in sums:
            total_map.setdefault(row['card_id'], {})[row['entry_type']] = float(row['total'] or 0)

        results = []
        for c in qs:
            a = assignments.get(c.id)
            tmap = total_map.get(c.id, {})
            pledged_ahadi = float(a.pledged_ahadi) if a else 0.0
            pledged_shukrani = float(a.pledged_shukrani) if a else 0.0
            pledged_majengo = float(a.pledged_majengo) if a else 0.0
            pa = tmap.get('AHADI', 0.0)
            ps = tmap.get('SHUKRANI', 0.0)
            pm = tmap.get('MAJENGO', 0.0)
            results.append(
                OfferingCardType(
                    id=str(c.id),
                    code=c.code,
                    street=c.street.name,
                    number=c.number,
                    is_taken=c.is_taken,
                    assigned_to_name=(c.assigned_to.full_name if getattr(c.assigned_to, 'full_name', None) else ''),
                    assigned_to_id=(str(c.assigned_to.id) if c.assigned_to else ''),
                    assignment_id=(str(a.id) if a else ''),
                    pledged_ahadi=pledged_ahadi,
                    pledged_shukrani=pledged_shukrani,
                    pledged_majengo=pledged_majengo,
                    progress_ahadi=(pa / pledged_ahadi * 100 if pledged_ahadi > 0 else 0.0),
                    progress_shukrani=(ps / pledged_shukrani * 100 if pledged_shukrani > 0 else 0.0),
                    progress_majengo=(pm / pledged_majengo * 100 if pledged_majengo > 0 else 0.0),
                )
            )
        return results

    def resolve_available_card_numbers(self, info, street_id=None):
        qs = OfferingCard.objects.filter(is_taken=False)
        if street_id:
            qs = qs.filter(street_id=street_id)
        return [
            AvailableCardNumberType(street=c.street.name, number=c.number, code=c.code)
            for c in qs.order_by('street__name', 'number')
        ]

    def resolve_cards_overview(self, info, street_id=None):
        qs = OfferingCard.objects.all()
        if street_id:
            qs = qs.filter(street_id=street_id)
        total_cards = qs.count()
        taken_cards = qs.filter(is_taken=True).count()
        free_cards = total_cards - taken_cards
        # activity: cards with at least one entry in current year
        year = timezone.now().year
        active_card_ids = (
            OfferingEntry.objects.filter(card_id__in=qs.values_list('id', flat=True), date__year=year)
            .values('card_id')
            .annotate(cnt=Count('id'))
        )
        actively_used_cards = sum(1 for _ in active_card_ids)
        # least active card: min sum of entries
        totals = (
            OfferingEntry.objects.filter(card_id__in=qs.values_list('id', flat=True))
            .values('card_id')
            .annotate(total=Sum('amount'))
            .order_by('total')
        )
        least_active_card = None
        if totals:
            first = list(totals)[0]
            code = OfferingCard.objects.filter(id=first['card_id']).values_list('code', flat=True).first()
            least_active_card = code

        ass_qs = CardAssignment.objects.filter(card_id__in=qs.values_list('id', flat=True))
        total_pledged_ahadi = float(ass_qs.aggregate(s=Sum('pledged_ahadi'))['s'] or 0)
        total_pledged_shukrani = float(ass_qs.aggregate(s=Sum('pledged_shukrani'))['s'] or 0)
        total_pledged_majengo = float(ass_qs.aggregate(s=Sum('pledged_majengo'))['s'] or 0)

        ent_qs = OfferingEntry.objects.filter(card_id__in=qs.values_list('id', flat=True))
        total_collected_ahadi = float(ent_qs.filter(entry_type='AHADI').aggregate(s=Sum('amount'))['s'] or 0)
        total_collected_shukrani = float(ent_qs.filter(entry_type='SHUKRANI').aggregate(s=Sum('amount'))['s'] or 0)
        total_collected_majengo = float(ent_qs.filter(entry_type='MAJENGO').aggregate(s=Sum('amount'))['s'] or 0)

        return CardsOverviewType(
            total_cards=total_cards,
            taken_cards=taken_cards,
            free_cards=free_cards,
            actively_used_cards=actively_used_cards,
            least_active_card=least_active_card or "",
            total_pledged_ahadi=total_pledged_ahadi,
            total_pledged_shukrani=total_pledged_shukrani,
            total_pledged_majengo=total_pledged_majengo,
            total_collected_ahadi=total_collected_ahadi,
            total_collected_shukrani=total_collected_shukrani,
            total_collected_majengo=total_collected_majengo,
        )

