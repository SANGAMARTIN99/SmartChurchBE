import graphene
from graphene_django.types import DjangoObjectType
from .models import Member

class MemberType(DjangoObjectType):
    class Meta:
        model = Member
        fields = ('id', 'full_name', 'email')

class LoginOutput(graphene.ObjectType):
    token = graphene.String()
    member = graphene.Field(MemberType)

class RegisterOutput(graphene.ObjectType):
    member = graphene.Field(MemberType)
    
class ForgotPasswordOutput(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()

class ResetPasswordOutput(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()