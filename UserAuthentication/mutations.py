import graphene
import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from graphene_django.types import DjangoObjectType
from .inputs import LoginInput, RegisterInput, ForgotPasswordInput, ResetPasswordInput
from .outputs import LoginOutput, RegisterOutput, ForgotPasswordOutput, ResetPasswordOutput
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from .models import Member, Street, Group, PasswordResetToken

class LoginUser(graphene.Mutation):
    class Arguments:
        input = LoginInput(required=True)

    Output = LoginOutput

    def mutate(self, info, input):
        user = authenticate(email=input.email, password=input.password)
        if not user:
            raise Exception('Invalid credentials')
        
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
        }, settings.SECRET_KEY, algorithm='HS256')
        
        return LoginOutput(token=token, member=user)

class RegisterUser(graphene.Mutation):
    class Arguments:
        input = RegisterInput(required=True)

    Output = RegisterOutput

    def mutate(self, info, input):
        if Member.objects.filter(email=input.email).exists():
            raise Exception('Email already exists')

        street = Street.objects.filter(id=input.street_id).first()
        if not street:
            raise Exception('Invalid street ID')

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

        return RegisterOutput(member=member)

class ForgotPassword(graphene.Mutation):
    class Arguments:
        input = ForgotPasswordInput(required=True)

    Output = ForgotPasswordOutput

    def mutate(self, info, input):
        try:
            member = Member.objects.get(email=input.email)
        except Member.DoesNotExist:
            return ForgotPasswordOutput(
                success=False,
                message=_('No account found with this email address')
            )

        # Create a password reset token
        reset_token = PasswordResetToken.objects.create(member=member)

        # Generate reset link
        reset_link = f"http://localhost:5173/reset-password/{reset_token.token}"

        # Render HTML email
        email_context = {'reset_link': reset_link}
        html_message = render_to_string('password_reset_email.html', email_context)

        # Send email
        try:
            send_mail(
                subject=_('Password Reset Request'),
                message=_(f'Click the following link to reset your password: {reset_link}\nThis link expires in 1 hour.'),
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member.email],
                fail_silently=False,
            )
            return ForgotPasswordOutput(
                success=True,
                message=_('Password reset link sent to your email')
            )
        except Exception as e:
            reset_token.delete()  # Delete token if email fails
            return ForgotPasswordOutput(
                success=False,
                message=_('Failed to send email. Please try again later.')
            )

class ResetPassword(graphene.Mutation):
    class Arguments:
        input = ResetPasswordInput(required=True)

    Output = ResetPasswordOutput

    def mutate(self, info, input):
        try:
            reset_token = PasswordResetToken.objects.get(token=input.token)
        except PasswordResetToken.DoesNotExist:
            return ResetPasswordOutput(
                success=False,
                message=_('Invalid or expired token')
            )

        if not reset_token.is_valid():
            reset_token.delete()
            return ResetPasswordOutput(
                success=False,
                message=_('Invalid or expired token')
            )

        member = reset_token.member
        member.set_password(input.password)
        member.save()

        # Delete the token after use
        reset_token.delete()

        return ResetPasswordOutput(
            success=True,
            message=_('Password reset successfully')
        )

class Mutation(graphene.ObjectType):
    login_user = LoginUser.Field()
    register_user = RegisterUser.Field()
    forgot_password = ForgotPassword.Field()
    reset_password = ResetPassword.Field()