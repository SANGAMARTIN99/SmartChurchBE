import graphene
from UserAuthentication.queries import Query
from UserAuthentication.mutations import Mutation
from Pastor.queries import PastorQuery
from Pastor.mutations import PastorMutation
from ChurchSecreatary.queries import SecretaryQuery
from ChurchSecreatary.mutations import SecretaryMutation

class RootQuery(Query, PastorQuery, SecretaryQuery, graphene.ObjectType):
    pass

class RootMutation(Mutation, PastorMutation, SecretaryMutation, graphene.ObjectType):  # <-- inherit from the class
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)