import graphene


class CreateOfferingCardInput(graphene.InputObjectType):
    street_id = graphene.Int(required=True)
    number = graphene.Int(required=True)


class AssignCardInput(graphene.InputObjectType):
    card_id = graphene.ID(required=True)
    member_id = graphene.ID()
    full_name = graphene.String(required=True)
    phone_number = graphene.String(required=True)
    year = graphene.Int(required=True)
    pledged_ahadi = graphene.Float(required=True)
    pledged_shukrani = graphene.Float(required=True)
    pledged_majengo = graphene.Float(required=True)


class UpdateAssignmentInput(graphene.InputObjectType):
    assignment_id = graphene.ID(required=True)
    full_name = graphene.String()
    phone_number = graphene.String()
    pledged_ahadi = graphene.Float()
    pledged_shukrani = graphene.Float()
    pledged_majengo = graphene.Float()
    active = graphene.Boolean()


class OfferingEntryInput(graphene.InputObjectType):
    card_id = graphene.ID(required=True)
    entry_type = graphene.String(required=True)  # AHADI | SHUKRANI | MAJENGO
    amount = graphene.Float(required=True)
    date = graphene.String()  # YYYY-MM-DD


class BulkGenerateCardsInput(graphene.InputObjectType):
    street_id = graphene.Int()  # if omitted, generate for all streets
    start_number = graphene.Int(default_value=1)
    end_number = graphene.Int(default_value=200)

