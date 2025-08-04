import graphene

class LoginInput(graphene.InputObjectType):
    email = graphene.String(required=True)
    password = graphene.String(required=True)

class RegisterInput(graphene.InputObjectType):
    full_name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone_number = graphene.String(required=False)
    street_id = graphene.Int(required=True)
    password = graphene.String(required=True)
    group_ids = graphene.List(graphene.Int, required=False)
    
class ForgotPasswordInput(graphene.InputObjectType):
    email = graphene.String(required=True)

class ResetPasswordInput(graphene.InputObjectType):
    token = graphene.String(required=True)
    password = graphene.String(required=True)