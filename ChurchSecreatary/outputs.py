import graphene


class SecretaryTaskType(graphene.ObjectType):
    id = graphene.ID()
    title = graphene.String()
    description = graphene.String()
    priority = graphene.String()
    status = graphene.String()
    due_date = graphene.String()
    assigned_to = graphene.String()
    category = graphene.String()


class MemberRequestType(graphene.ObjectType):
    id = graphene.ID()
    member_name = graphene.String()
    request_type = graphene.String()
    status = graphene.String()
    submitted_date = graphene.String()
    urgency = graphene.String()
    details = graphene.String()


class QuickStatType(graphene.ObjectType):
    title = graphene.String()
    value = graphene.Int()
    change = graphene.Int()
    trend = graphene.String()  # 'up' | 'down'


class ActivityLogType(graphene.ObjectType):
    action = graphene.String()
    user = graphene.String()
    time = graphene.String()
    type = graphene.String()  # success | warning | info


class OfferingCardType(graphene.ObjectType):
    id = graphene.ID()
    code = graphene.String()
    street = graphene.String()
    number = graphene.Int()
    is_taken = graphene.Boolean()
    assigned_to_name = graphene.String()
    assigned_to_id = graphene.String()
    assignment_id = graphene.String()
    assigned_phone = graphene.String()
    assigned_year = graphene.Int()
    pledged_ahadi = graphene.Float()
    pledged_shukrani = graphene.Float()
    pledged_majengo = graphene.Float()
    progress_ahadi = graphene.Float()
    progress_shukrani = graphene.Float()
    progress_majengo = graphene.Float()


class AvailableCardNumberType(graphene.ObjectType):
    street = graphene.String()
    number = graphene.Int()
    code = graphene.String()


class CardAssignmentType(graphene.ObjectType):
    id = graphene.ID()
    card_code = graphene.String()
    full_name = graphene.String()
    phone_number = graphene.String()
    year = graphene.Int()
    pledged_ahadi = graphene.Float()
    pledged_shukrani = graphene.Float()
    pledged_majengo = graphene.Float()
    active = graphene.Boolean()


class OfferingEntryType(graphene.ObjectType):
    id = graphene.ID()
    card_code = graphene.String()
    entry_type = graphene.String()
    amount = graphene.Float()
    date = graphene.String()


class CardsOverviewType(graphene.ObjectType):
    total_cards = graphene.Int()
    taken_cards = graphene.Int()
    free_cards = graphene.Int()
    actively_used_cards = graphene.Int()
    least_active_card = graphene.String()
    total_pledged_ahadi = graphene.Float()
    total_pledged_shukrani = graphene.Float()
    total_pledged_majengo = graphene.Float()
    total_collected_ahadi = graphene.Float()
    total_collected_shukrani = graphene.Float()
    total_collected_majengo = graphene.Float()


class CardApplicationType(graphene.ObjectType):
    id = graphene.ID()
    full_name = graphene.String()
    phone_number = graphene.String()
    street = graphene.String()
    preferred_number = graphene.Int()
    note = graphene.String()
    pledged_ahadi = graphene.Float()
    pledged_shukrani = graphene.Float()
    pledged_majengo = graphene.Float()
    status = graphene.String()
    created_at = graphene.String()


class RegistrationWindowStatusType(graphene.ObjectType):
    is_open = graphene.Boolean()
    start_at = graphene.String()
    end_at = graphene.String()


class NumberSuggestionResultType(graphene.ObjectType):
    street = graphene.String()
    query_number = graphene.Int()
    exact_available = graphene.Boolean()
    exact_code = graphene.String()
    suggestions = graphene.List(AvailableCardNumberType)


class OfferingEntryItemType(graphene.ObjectType):
    code = graphene.String()
    date = graphene.String()
    entry_type = graphene.String()
    amount = graphene.Float()


class MemberOfferingHistoryType(graphene.ObjectType):
    member_id = graphene.ID()
    year = graphene.Int()
    entries = graphene.List(OfferingEntryItemType)
    total_ahadi = graphene.Float()
    total_shukrani = graphene.Float()
    total_majengo = graphene.Float()


class MyCardStateType(graphene.ObjectType):
    has_pending_application = graphene.Boolean()
    has_current_assignment = graphene.Boolean()


class OfferingBatchType(graphene.ObjectType):
    id = graphene.ID()
    street = graphene.String()
    recorder_name = graphene.String()
    date = graphene.String()
    mass_type = graphene.String()
    major_mass_number = graphene.Int()
    created_at = graphene.String()


class BulkOfferingResultType(graphene.ObjectType):
    ok = graphene.Boolean()
    batch = graphene.Field(OfferingBatchType)
    count = graphene.Int()
    total_ahadi = graphene.Float()
    total_shukrani = graphene.Float()
    total_majengo = graphene.Float()
