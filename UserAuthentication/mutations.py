import graphene
import graphql_jwt
import jwt
from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from graphene_django.types import DjangoObjectType
from .models import Member, Street, Group, PasswordResetToken
from .inputs import LoginInput, RegisterInput, ForgotPasswordInput, ResetPasswordInput
from .outputs import LoginOutput, RegisterOutput, ForgotPasswordOutput, ResetPasswordOutput
import datetime
import time
import logging

logger = logging.getLogger(__name__)

class LoginUser(graphene.Mutation):
    class Arguments:
        input = LoginInput(required=True)

    Output = LoginOutput

    def mutate(self, info, input):
        user = authenticate(email=input.email, password=input.password)
        if not user:
            logger.error(f'Invalid credentials for email: {input.email}')
            raise Exception(_('Invalid credentials'))
        
        access_token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'exp': int(time.time() + 15 * 60)  # 15 minutes from now
        }, settings.SECRET_KEY, algorithm='HS256')
        
        refresh_token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'exp': int(time.time() + 7 * 24 * 60 * 60)  # 7 days from now
        }, settings.SECRET_KEY, algorithm='HS256')
        
        logger.info(f'Login successful for user {user.id}: access_token generated')
        return LoginOutput(access_token=access_token, refresh_token=refresh_token, member=user)

class RegisterUser(graphene.Mutation):
    class Arguments:
        input = RegisterInput(required=True)

    Output = RegisterOutput

    def mutate(self, info, input):
        if Member.objects.filter(email=input.email).exists():
            logger.error(f'Email already exists: {input.email}')
            raise Exception(_('Email already exists'))

        street = Street.objects.filter(id=input.street_id).first()
        if not street:
            logger.error(f'Invalid street ID: {input.street_id}')
            raise Exception(_('Invalid street ID'))

        member = Member.objects.create_user(
            email=input.email,
            full_name=input.full_name,
            password=input.password,
            phone_number=input.phone_number,
            street=street
        )

        if input.group_ids:
            groups = Group.objects.filter(id__in=input.group_ids)
            member.groups.set(groups)

        logger.info(f'Registered new user {member.id}: {member.email}')
        return RegisterOutput(member=member)

class ForgotPassword(graphene.Mutation):
    class Arguments:
        input = ForgotPasswordInput(required=True)

    Output = ForgotPasswordOutput

    def mutate(self, info, input):
        try:
            member = Member.objects.get(email=input.email)
        except Member.DoesNotExist:
            logger.error(f'No account found for email: {input.email}')
            return ForgotPasswordOutput(
                success=False,
                message=_('No account found with this email address')
            )

        reset_token = PasswordResetToken.objects.create(member=member)
        reset_link = f"http://localhost:5173/reset-password/{reset_token.token}"

        try:
            email_context = {'reset_link': reset_link}
            html_message = render_to_string('emails/password_reset_email.html', email_context)

            send_mail(
                subject=_('Password Reset Request'),
                message=_(f'Click the following link to reset your password: {reset_link}\nThis link expires in 1 hour.'),
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member.email],
                fail_silently=False,
            )
            logger.info(f'Password reset link sent to {member.email}')
            return ForgotPasswordOutput(
                success=True,
                message=_('Password reset link sent to your email')
            )
        except TemplateDoesNotExist:
            reset_token.delete()
            logger.error('Failed to render email template')
            return ForgotPasswordOutput(
                success=False,
                message=_('Failed to render email template. Please contact support.')
            )
        except Exception as e:
            reset_token.delete()
            logger.error(f'Failed to send email: {str(e)}')
            return ForgotPasswordOutput(
                success=False,
                message=_('Failed to send email. Please try again later.') + f' ({str(e)})'
            )

class ResetPassword(graphene.Mutation):
    class Arguments:
        input = ResetPasswordInput(required=True)

    Output = ResetPasswordOutput

    def mutate(self, info, input):
        try:
            reset_token = PasswordResetToken.objects.get(token=input.token)
        except PasswordResetToken.DoesNotExist:
            logger.error('Invalid or expired token')
            return ResetPasswordOutput(
                success=False,
                message=_('Invalid or expired token')
            )

        if not reset_token.is_valid():
            reset_token.delete()
            logger.error('Invalid or expired token')
            return ResetPasswordOutput(
                success=False,
                message=_('Invalid or expired token')
            )

        member = reset_token.member
        member.set_password(input.password)
        member.save()

        reset_token.delete()

        logger.info(f'Password reset successful for {member.email}')
        return ResetPasswordOutput(
            success=True,
            message=_('Password reset successfully')
        )

class RefreshToken(graphene.Mutation):
    class Arguments:
        refresh_token = graphene.String(required=True)

    access_token = graphene.String()

    def mutate(self, info, refresh_token):
        logger.info(f'Received refresh_token: {refresh_token}')
        try:
            if not refresh_token:
                raise Exception('No refresh token provided')
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            logger.info(f'Decoded refresh_token payload: {payload}')
            user = Member.objects.filter(id=payload['user_id']).first()
            if not user:
                raise Exception(f'User with ID {payload["user_id"]} not found')
            access_token = jwt.encode({
                'user_id': user.id,
                'email': user.email,
                'exp': int(time.time() + 15 * 60)
            }, settings.SECRET_KEY, algorithm='HS256')
            logger.info(f'Generated new access_token for user {user.id}')
            return RefreshToken(access_token=access_token)
        except jwt.ExpiredSignatureError:
            logger.error('Refresh token expired')
            raise Exception('Refresh token expired')
        except jwt.InvalidTokenError as e:
            logger.error(f'Invalid refresh token: {str(e)}')
            raise Exception(f'Invalid refresh token: {str(e)}')
        except Exception as e:
            logger.error(f'Refresh token error: {str(e)}')
            raise Exception(f'Refresh token error: {str(e)}')

class Logout(graphene.Mutation):
    class Meta:
        output = graphene.Boolean

    @staticmethod
    def mutate(root, info):
        logout(info.context)
        return True

class Mutation(graphene.ObjectType):
    login_user = LoginUser.Field()
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    register_user = RegisterUser.Field()
    forgot_password = ForgotPassword.Field()
    reset_password = ResetPassword.Field()
    refresh_token = RefreshToken.Field()
    logout = Logout.Field()