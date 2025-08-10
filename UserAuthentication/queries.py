from venv import logger
import graphene
from graphene_django.types import DjangoObjectType
from UserAuthentication.models import *
from UserAuthentication.mutations import Mutation
import jwt
from django.conf import settings
import logging


class MemberType(DjangoObjectType):
    class Meta:
        model = Member
        fields = ('id', 'email', 'full_name', 'phone_number', 'street', 'groups', 'role')
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
    me = graphene.Field(MemberType)
    
    def resolve_streets(self, info):
        return Street.objects.all()

    def resolve_groups(self, info):
        return Group.objects.all()

    def resolve_me(self, info):
        logger.info('Resolving ME_QUERY')
        # Manually extract and validate token from header
        auth_header = info.context.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            logger.error('No Authorization header provided')
            raise Exception('No Authorization header provided')
        
        if not auth_header.startswith('Bearer '):
            logger.error('Invalid Authorization header format')
            raise Exception('Invalid Authorization header format')
        
        token = auth_header.split(' ')[1]
        logger.info(f'Extracted token: {token}')
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            logger.info(f'Decoded payload: {payload}')
            user = Member.objects.filter(id=payload['user_id'], email=payload['email']).first()
            if not user:
                logger.error(f'User not found: {payload["user_id"]}')
                raise Exception('User not found')
            logger.info(f'Authenticated user: {user.id}, {user.email}')
            return user
        except jwt.ExpiredSignatureError:
            logger.error('Token expired')
            raise Exception('Token expired')
        except jwt.InvalidTokenError as e:
            logger.error(f'Invalid token: {str(e)}')
            raise Exception(f'Invalid token: {str(e)}')
        except Exception as e:
            logger.error(f'Authentication error: {str(e)}')
            raise Exception(f'Authentication error: {str(e)}')