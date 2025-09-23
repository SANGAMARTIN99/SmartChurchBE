import graphene
from UserAuthentication.queries import Query
from UserAuthentication.mutations import Mutation
from Pastor.queries import PastorQuery
from Pastor.mutations import PastorMutation

class RootQuery(Query,PastorQuery, graphene.ObjectType):
    pass

class RootMutation(Mutation,PastorMutation, graphene.ObjectType):  # <-- inherit from the class
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)