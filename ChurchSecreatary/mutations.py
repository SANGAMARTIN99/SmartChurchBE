import graphene
from django.utils import timezone
from datetime import datetime

from UserAuthentication.models import Street, Member
from .models import OfferingCard, CardAssignment, OfferingEntry, CardApplication, RegistrationWindow, OfferingBatch, ActivityLog
from .outputs import CardAssignmentType, OfferingEntryType, CardApplicationType, RegistrationWindowStatusType, BulkOfferingResultType, OfferingBatchType
from .Inputs import CreateOfferingCardInput, AssignCardInput, UpdateAssignmentInput, OfferingEntryInput, BulkGenerateCardsInput, CardApplicationInput, BulkOfferingEntryInput
from churchMember.models import Offering as CMOffering


class CreateOfferingCard(graphene.Mutation):
    class Arguments:
        input = CreateOfferingCardInput(required=True)

    ok = graphene.Boolean()
    card_code = graphene.String()
    card_id = graphene.ID()

    def mutate(self, info, input: CreateOfferingCardInput):
        street = Street.objects.filter(id=input.street_id).first()
        if not street:
            raise Exception("Street not found")
        # Ensure number unique per street
        if OfferingCard.objects.filter(street=street, number=input.number).exists():
            raise Exception("Card number already exists for this street")
        card = OfferingCard(street=street, number=input.number)
        card.save()
        return CreateOfferingCard(ok=True, card_code=card.code, card_id=str(card.id))


class AssignCard(graphene.Mutation):
    class Arguments:
        input = AssignCardInput(required=True)

    ok = graphene.Boolean()
    assignment = graphene.Field(CardAssignmentType)

    def mutate(self, info, input: AssignCardInput):
        card = OfferingCard.objects.filter(id=input.card_id).first()
        if not card:
            raise Exception("Card not found")

        # Prevent duplicate assignment for the same card and year
        existing_for_year = CardAssignment.objects.filter(card=card, year=input.year).first()
        if existing_for_year:
            raise Exception("This card already has an assignment for the specified year")

        member = None
        if input.member_id:
            member = Member.objects.filter(id=input.member_id).first()

        assign = CardAssignment.objects.create(
            card=card,
            member=member,
            full_name=input.full_name,
            phone_number=input.phone_number,
            year=input.year,
            pledged_ahadi=input.pledged_ahadi,
            pledged_shukrani=input.pledged_shukrani,
            pledged_majengo=input.pledged_majengo,
            active=True,
        )
        # Only mark the card as taken for the current active year
        try:
            current_year = timezone.now().year
        except Exception:
            current_year = input.year
        if input.year == current_year:
            card.is_taken = True
            card.assigned_to = member
            card.assigned_at = timezone.now()
            card.save()

        return AssignCard(ok=True, assignment=CardAssignmentType(
            id=str(assign.id),
            card_code=card.code,
            full_name=assign.full_name,
            phone_number=assign.phone_number,
            year=assign.year,
            pledged_ahadi=float(assign.pledged_ahadi),
            pledged_shukrani=float(assign.pledged_shukrani),
            pledged_majengo=float(assign.pledged_majengo),
            active=assign.active,
        ))


class UpdateAssignment(graphene.Mutation):
    class Arguments:
        input = UpdateAssignmentInput(required=True)

    ok = graphene.Boolean()
    assignment = graphene.Field(CardAssignmentType)

    def mutate(self, info, input: UpdateAssignmentInput):
        assign = CardAssignment.objects.filter(id=input.assignment_id).first()
        if not assign:
            raise Exception("Assignment not found")
        if input.full_name is not None:
            assign.full_name = input.full_name
        if input.phone_number is not None:
            assign.phone_number = input.phone_number
        if input.pledged_ahadi is not None:
            assign.pledged_ahadi = input.pledged_ahadi
        if input.pledged_shukrani is not None:
            assign.pledged_shukrani = input.pledged_shukrani
        if input.pledged_majengo is not None:
            assign.pledged_majengo = input.pledged_majengo
        if input.active is not None:
            assign.active = input.active
        assign.save()
        return UpdateAssignment(ok=True, assignment=CardAssignmentType(
            id=str(assign.id),
            card_code=assign.card.code,
            full_name=assign.full_name,
            phone_number=assign.phone_number,
            year=assign.year,
            pledged_ahadi=float(assign.pledged_ahadi),
            pledged_shukrani=float(assign.pledged_shukrani),
            pledged_majengo=float(assign.pledged_majengo),
            active=assign.active,
        ))


class RecordOfferingEntry(graphene.Mutation):
    class Arguments:
        input = OfferingEntryInput(required=True)

    ok = graphene.Boolean()
    entry = graphene.Field(OfferingEntryType)

    def mutate(self, info, input: OfferingEntryInput):
        card = OfferingCard.objects.filter(id=input.card_id).first()
        if not card:
            raise Exception("Card not found")
        dt = None
        if input.date:
            try:
                dt = datetime.strptime(input.date, "%Y-%m-%d").date()
            except Exception:
                raise Exception("Invalid date format, expected YYYY-MM-DD")
        entry = OfferingEntry.objects.create(
            card=card,
            entry_type=input.entry_type,
            amount=input.amount,
            date=dt or timezone.now().date(),
        )
        # Best-effort sync to churchMember.Offering so dashboards remain consistent
        try:
            ent_date = entry.date
            # Prefer active assignment for the entry year
            assign = (
                CardAssignment.objects
                .filter(card=card, year=getattr(ent_date, 'year', timezone.now().year))
                .order_by('-active')
                .first()
            )
            cm_member = assign.member if assign else None
            CMOffering.objects.create(
                member=cm_member,
                amount=entry.amount,
                offering_type=entry.entry_type,
                mass_type='MAJOR',  # single-entry API lacks mass context
                street=card.street,
                date=entry.date,
                attendant=None,
            )
        except Exception:
            pass
        return RecordOfferingEntry(ok=True, entry=OfferingEntryType(
            id=str(entry.id),
            card_code=card.code,
            entry_type=entry.entry_type,
            amount=float(entry.amount),
            date=entry.date.strftime('%Y-%m-%d'),
        ))


class CreateCardApplication(graphene.Mutation):
    class Arguments:
        input = CardApplicationInput(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(CardApplicationType)
    def mutate(self, info, input: CardApplicationInput):
        street = Street.objects.filter(id=input.street_id).first()
        if not street:
            raise Exception("Street not found")

        # Attach the logged-in member if available with robust fallbacks
        member = None
        try:
            user = info.context.user
            if user and getattr(user, 'is_authenticated', False):
                # Prefer explicit relation
                member = getattr(user, 'member', None)
                if member is None:
                    # Common pattern: Member has OneToOne to auth user
                    from .models import Member as MemberModel
                    member = MemberModel.objects.filter(user=user).first()
        except Exception:
            member = None
        # As a final fallback, try to match member by phone number (if unique in your data)
        if member is None:
            try:
                from .models import Member as MemberModel
                member = MemberModel.objects.filter(phone_number=input.phone_number).first()
            except Exception:
                member = None

        # Block duplicate: if member already has a NEW application or a current-year active assignment
        if member:
            if CardApplication.objects.filter(member=member, status=CardApplication.Status.NEW).exists():
                raise Exception("You already have a pending application")
            current_year = timezone.now().year
            if CardAssignment.objects.filter(member=member, year=current_year, active=True).exists():
                raise Exception("You already have an assigned card for the current year")


        app = CardApplication.objects.create(
            member=member,
            full_name=input.full_name,
            phone_number=input.phone_number,
            street=street,
            preferred_number=getattr(input, 'preferred_number', None),
            note=getattr(input, 'note', '') or '',
            pledged_ahadi=getattr(input, 'pledged_ahadi', 0) or 0,
            pledged_shukrani=getattr(input, 'pledged_shukrani', 0) or 0,
            pledged_majengo=getattr(input, 'pledged_majengo', 0) or 0,
        )

        # If registration window is OPEN, auto-assign a card immediately
        is_open, start_at, end_at = RegistrationWindow.current_status()
        if is_open:
            current_year = timezone.now().year
            card = None
            # Try preferred number if provided and available
            pref = getattr(input, 'preferred_number', None)
            if pref:
                card = OfferingCard.objects.filter(street=street, number=pref).first()
                # Consider free if not taken for current year
                if card:
                    if CardAssignment.objects.filter(card=card, year=current_year).exists():
                        card = None
            # Else pick the first free card in this street
            if not card:
                # free means no assignment for current year
                taken_ids = CardAssignment.objects.filter(year=current_year).values_list('card_id', flat=True)
                card = OfferingCard.objects.filter(street=street).exclude(id__in=list(taken_ids)).order_by('number').first()
            if card:
                assign = CardAssignment.objects.create(
                    card=card,
                    member=member,
                    full_name=app.full_name,
                    phone_number=app.phone_number,
                    year=current_year,
                    pledged_ahadi=float(app.pledged_ahadi or 0),
                    pledged_shukrani=float(app.pledged_shukrani or 0),
                    pledged_majengo=float(app.pledged_majengo or 0),
                    active=True,
                )
                # Mark taken for current year
                card.is_taken = True
                card.assigned_to = member
                card.assigned_at = timezone.now()
                card.save()

                # Link and finalize application
                app.assignment = assign
                app.status = CardApplication.Status.APPROVED
                app.pledged_ahadi = 0
                app.pledged_shukrani = 0
                app.pledged_majengo = 0
                app.preferred_number = None
                app.save()

        return CreateCardApplication(ok=True, application=CardApplicationType(
            id=str(app.id),
            full_name=app.full_name,
            phone_number=app.phone_number,
            street=app.street.name,
            preferred_number=app.preferred_number or None,
            note=app.note,
            pledged_ahadi=float(app.pledged_ahadi),
            pledged_shukrani=float(app.pledged_shukrani),
            pledged_majengo=float(app.pledged_majengo),
            status=app.status,
            created_at=app.created_at.strftime('%Y-%m-%d %H:%M'),
        ))


class SecretaryMutation(graphene.ObjectType):
    create_offering_card = CreateOfferingCard.Field()
    assign_card = AssignCard.Field()
    update_assignment = UpdateAssignment.Field()
    record_offering_entry = RecordOfferingEntry.Field()
    create_card_application = CreateCardApplication.Field()


class BulkGenerateCards(graphene.Mutation):
    class Arguments:
        input = BulkGenerateCardsInput(required=True)

    ok = graphene.Boolean()
    created = graphene.Int()
    skipped = graphene.Int()

    def mutate(self, info, input: BulkGenerateCardsInput):
        streets = []
        if input.street_id:
            st = Street.objects.filter(id=input.street_id).first()
            if not st:
                raise Exception("Street not found")
            streets = [st]
        else:
            streets = list(Street.objects.all())

        start = max(1, int(input.start_number or 1))
        end = min(300, int(input.end_number or 300))
        if start > end:
            raise Exception("start_number cannot be greater than end_number")

        created = 0
        skipped = 0
        for st in streets:
            for n in range(start, end + 1):
                if OfferingCard.objects.filter(street=st, number=n).exists():
                    skipped += 1
                    continue
                card = OfferingCard(street=st, number=n)
                card.save()
                created += 1

        return BulkGenerateCards(ok=True, created=created, skipped=skipped)


class SecretaryMutation(SecretaryMutation):
    bulk_generate_cards = BulkGenerateCards.Field()


class OpenRegistrationWindow(graphene.Mutation):
    class Arguments:
        start_at = graphene.String(required=True)  # ISO datetime
        end_at = graphene.String(required=True)

    ok = graphene.Boolean()
    window = graphene.Field(RegistrationWindowStatusType)

    def mutate(self, info, start_at: str, end_at: str):
        try:
            start_dt = datetime.fromisoformat(start_at)
            end_dt = datetime.fromisoformat(end_at)
        except Exception:
            raise Exception("Invalid datetime format; expected ISO8601, e.g., 2025-01-31T08:00:00")
        if end_dt <= start_dt:
            raise Exception("end_at must be after start_at")
        # Close previous active windows
        RegistrationWindow.objects.filter(is_open=True).update(is_open=False)
        w = RegistrationWindow.objects.create(start_at=start_dt, end_at=end_dt, is_open=True)
        return OpenRegistrationWindow(
            ok=True,
            window=RegistrationWindowStatusType(
                is_open=True,
                start_at=w.start_at.isoformat(timespec='seconds'),
                end_at=w.end_at.isoformat(timespec='seconds'),
            ),
        )


class CloseRegistrationWindow(graphene.Mutation):
    ok = graphene.Boolean()
    window = graphene.Field(RegistrationWindowStatusType)

    def mutate(self, info):
        w = RegistrationWindow.objects.filter(is_open=True).order_by('-created_at').first()
        if not w:
            return CloseRegistrationWindow(ok=True, window=RegistrationWindowStatusType(is_open=False, start_at=None, end_at=None))
        w.is_open = False
        w.save()
        return CloseRegistrationWindow(ok=True, window=RegistrationWindowStatusType(is_open=False, start_at=w.start_at.isoformat(timespec='seconds'), end_at=w.end_at.isoformat(timespec='seconds')))


class SecretaryMutation(SecretaryMutation):
    open_registration_window = OpenRegistrationWindow.Field()
    close_registration_window = CloseRegistrationWindow.Field()


class ApproveCardApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)
        card_id = graphene.ID(required=True)
        year = graphene.Int(required=True)
        # Optional overrides; if omitted, use application requested pledges
        pledged_ahadi = graphene.Float()
        pledged_shukrani = graphene.Float()
        pledged_majengo = graphene.Float()

    ok = graphene.Boolean()
    assignment = graphene.Field(CardAssignmentType)

    def mutate(self, info, application_id, card_id, year, pledged_ahadi=None, pledged_shukrani=None, pledged_majengo=None):
        app = CardApplication.objects.filter(id=application_id).select_related('member', 'street', 'assignment').first()
        if not app:
            raise Exception("Application not found")
        if app.assignment_id:
            raise Exception("Application already approved and linked to an assignment")
        card = OfferingCard.objects.filter(id=card_id).first()
        if not card:
            raise Exception("Card not found")
        # prevent duplicate assignment for this year
        if CardAssignment.objects.filter(card=card, year=year).exists():
            raise Exception("This card already has an assignment for the specified year")

        member = app.member  # may be None
        a_ahadi = pledged_ahadi if pledged_ahadi is not None else float(app.pledged_ahadi or 0)
        a_shukrani = pledged_shukrani if pledged_shukrani is not None else float(app.pledged_shukrani or 0)
        a_majengo = pledged_majengo if pledged_majengo is not None else float(app.pledged_majengo or 0)

        assign = CardAssignment.objects.create(
            card=card,
            member=member,
            full_name=app.full_name,
            phone_number=app.phone_number,
            year=year,
            pledged_ahadi=a_ahadi,
            pledged_shukrani=a_shukrani,
            pledged_majengo=a_majengo,
            active=True,
        )

        # Mark card taken if current year
        current_year = timezone.now().year
        if year == current_year:
            card.is_taken = True
            card.assigned_to = member
            card.assigned_at = timezone.now()
            card.save()

        # Link and clear temporary requested pledges, set status approved
        app.assignment = assign
        app.status = CardApplication.Status.APPROVED
        app.pledged_ahadi = 0
        app.pledged_shukrani = 0
        app.pledged_majengo = 0
        app.save()

        return ApproveCardApplication(
            ok=True,
            assignment=CardAssignmentType(
                id=str(assign.id),
                card_code=assign.card.code,
                full_name=assign.full_name,
                phone_number=assign.phone_number,
                year=assign.year,
                pledged_ahadi=float(assign.pledged_ahadi),
                pledged_shukrani=float(assign.pledged_shukrani),
                pledged_majengo=float(assign.pledged_majengo),
                active=assign.active,
            ),
        )


class SecretaryMutation(SecretaryMutation):
    approve_card_application = ApproveCardApplication.Field()


class RejectCardApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)
        reason = graphene.String()

    ok = graphene.Boolean()
    application = graphene.Field(CardApplicationType)

    def mutate(self, info, application_id, reason=None):
        app = CardApplication.objects.filter(id=application_id).first()
        if not app:
            raise Exception("Application not found")
        if app.status == CardApplication.Status.APPROVED:
            raise Exception("Cannot reject an already approved application")
        app.status = CardApplication.Status.REJECTED
        if reason:
            app.note = (app.note or '') + ("\nReason: " + reason)
        app.save()
        return RejectCardApplication(ok=True, application=CardApplicationType(
            id=str(app.id),
            full_name=app.full_name,
            phone_number=app.phone_number,
            street=app.street.name,
            preferred_number=app.preferred_number or None,
            note=app.note,
            pledged_ahadi=float(app.pledged_ahadi or 0),
            pledged_shukrani=float(app.pledged_shukrani or 0),
            pledged_majengo=float(app.pledged_majengo or 0),
            status=app.status,
            created_at=app.created_at.strftime('%Y-%m-%d %H:%M'),
        ))


class SecretaryMutation(SecretaryMutation):
    reject_card_application = RejectCardApplication.Field()


class BulkRecordOfferingEntries(graphene.Mutation):
    class Arguments:
        input = BulkOfferingEntryInput(required=True)

    Output = BulkOfferingResultType

    def mutate(self, info, input: BulkOfferingEntryInput):
        # Validate meta
        meta = input.meta
        street = Street.objects.filter(id=meta.street_id).first()
        if not street:
            raise Exception("Street not found")
        try:
            batch_date = datetime.strptime(meta.date, "%Y-%m-%d").date()
        except Exception:
            raise Exception("Invalid date format for meta.date, expected YYYY-MM-DD")

        mass_type = (meta.mass_type or '').upper()
        allowed_mass = {"MAJOR", "MORNING_GLORY", "EVENING_GLORY", "SELI"}
        if mass_type not in allowed_mass:
            raise Exception("Invalid mass_type")
        major_num = getattr(meta, 'major_mass_number', None)
        if mass_type == "MAJOR" and (major_num not in (1, 2)):
            raise Exception("major_mass_number must be 1 or 2 when mass_type is MAJOR")

        # Create batch
        batch = OfferingBatch.objects.create(
            street=street,
            recorder_name=meta.recorder_name,
            date=batch_date,
            mass_type=mass_type,
            major_mass_number=major_num if mass_type == "MAJOR" else None,
        )

        # Process entries
        total_ahadi = 0.0
        total_shukrani = 0.0
        total_majengo = 0.0
        count = 0
        for item in input.entries or []:
            card = OfferingCard.objects.filter(id=item.card_id).select_related('street').first()
            if not card:
                raise Exception("Card not found: " + str(item.card_id))
            if card.street_id != street.id:
                raise Exception(f"Card {card.code} does not belong to selected street")
            # per-entry date
            if getattr(item, 'date', None):
                try:
                    ent_date = datetime.strptime(item.date, "%Y-%m-%d").date()
                except Exception:
                    raise Exception("Invalid date format in entries, expected YYYY-MM-DD")
            else:
                ent_date = batch_date

            entry = OfferingEntry.objects.create(
                card=card,
                entry_type=item.entry_type,
                amount=item.amount,
                date=ent_date,
                batch=batch,
            )
            # Best-effort sync to churchMember.Offering with batch mass context
            try:
                assign = (
                    CardAssignment.objects
                    .filter(card=card, year=getattr(ent_date, 'year', timezone.now().year))
                    .order_by('-active')
                    .first()
                )
                cm_member = assign.member if assign else None
                CMOffering.objects.create(
                    member=cm_member,
                    amount=entry.amount,
                    offering_type=entry.entry_type,
                    mass_type=batch.mass_type,
                    street=card.street,
                    date=entry.date,
                    attendant=None,
                )
            except Exception:
                pass
            amt = float(entry.amount)
            et = entry.entry_type
            if et == 'AHADI':
                total_ahadi += amt
            elif et == 'SHUKRANI':
                total_shukrani += amt
            elif et == 'MAJENGO':
                total_majengo += amt
            count += 1

        # Activity log
        try:
            ActivityLog.objects.create(
                action=f"Recorded {count} entries: A={total_ahadi:.2f}, S={total_shukrani:.2f}, M={total_majengo:.2f} for {street.name} on {batch_date}",
                user=getattr(info.context, 'user', None),
                type=ActivityLog.Type.SUCCESS,
            )
        except Exception:
            pass

        return BulkOfferingResultType(
            ok=True,
            batch=OfferingBatchType(
                id=str(batch.id),
                street=street.name,
                recorder_name=batch.recorder_name,
                date=batch.date.strftime('%Y-%m-%d'),
                mass_type=batch.mass_type,
                major_mass_number=batch.major_mass_number or None,
                created_at=batch.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ),
            count=count,
            total_ahadi=total_ahadi,
            total_shukrani=total_shukrani,
            total_majengo=total_majengo,
        )


class SecretaryMutation(SecretaryMutation):
    bulk_record_offering_entries = BulkRecordOfferingEntries.Field()

