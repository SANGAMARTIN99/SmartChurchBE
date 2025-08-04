import graphene
from UserAuthentication.queries import Query
from UserAuthentication.mutations import Mutation

class RootQuery(Query, graphene.ObjectType):
    pass

class RootMutation(Mutation, graphene.ObjectType):  # <-- inherit from the class
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)