import graphene
from graphene_django.types import DjangoObjectType
from .models import Street, Group

class StreetType(DjangoObjectType):
    class Meta:
        model = Street
        fields = ('id', 'name')

class GroupType(DjangoObjectType):
    class Meta:
        model = Group
        fields = ('id', 'name')

class Query(graphene.ObjectType):
    streets = graphene.List(StreetType)
    groups = graphene.List(GroupType)

    def resolve_streets(self, info):
        return Street.objects.all()

    def resolve_groups(self, info):
        return Group.objects.all()