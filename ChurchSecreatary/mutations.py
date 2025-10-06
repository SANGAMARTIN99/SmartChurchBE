import graphene
from django.utils import timezone
from datetime import datetime

from UserAuthentication.models import Street, Member
from .models import OfferingCard, CardAssignment, OfferingEntry
from .outputs import CardAssignmentType, OfferingEntryType
from .Inputs import CreateOfferingCardInput, AssignCardInput, UpdateAssignmentInput, OfferingEntryInput, BulkGenerateCardsInput


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
        if card.is_taken:
            raise Exception("Card already assigned")

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
        return RecordOfferingEntry(ok=True, entry=OfferingEntryType(
            id=str(entry.id),
            card_code=card.code,
            entry_type=entry.entry_type,
            amount=float(entry.amount),
            date=entry.date.strftime('%Y-%m-%d'),
        ))


class SecretaryMutation(graphene.ObjectType):
    create_offering_card = CreateOfferingCard.Field()
    assign_card = AssignCard.Field()
    update_assignment = UpdateAssignment.Field()
    record_offering_entry = RecordOfferingEntry.Field()


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
        end = min(200, int(input.end_number or 200))
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

