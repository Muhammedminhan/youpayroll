import logging

from django.core.exceptions import ValidationError
from django.db import transaction

import graphene
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError
from core.decorators import login_required
from payees.models import Payee, BankDetails, BankDetailsAck
from payees.upload_helpers import validate_image

logger = logging.getLogger(__name__)


class PayeeType(DjangoObjectType):
    class Meta:
        """
        This section displays the personal data of the payee or employee,
        including their status (active or inactive) and other bank benefits.
        """
        model = Payee
        fields = ('status', 'hrm_id', 'user', 'tds_type', 'full_name', 'email',
                  'pan_no', 'date_of_joining', 'address', 'is_dark_mode')


class BankDetailsType(DjangoObjectType):
    class Meta:
        """
        This section displays the bank details of the employee.
        """
        model = BankDetails
        fields = ('payee', 'bank_name', 'account_no', 'account_holder_name',
                  'account_type', 'ifsc_code',
                  'micr_code', 'swift_code', 'branch_address',
                  'payee_acknowledgement')


class BankDetailsAckType(DjangoObjectType):
    class Meta:
        """
        This section indicates whether the payee has acknowledged the bank details,
        showing the bank acknowledgment status as either True or False.
        """
        model = BankDetailsAck
        fields = [
            'payee', 'uploaded_date', 'is_approved', 'correction_comments',
            'bank_details_screenshot']


class BaseMutation(graphene.Mutation):
    """
    Base mutation class with common functionality:
    - Authorization check
    - Payee fetching
    - Error handling
    """

    class Meta:
        abstract = True

    @classmethod
    def check_authorization(cls, context):
        """
        Ensures the user is authenticated.
        """
        if not context.user.is_authenticated:
            raise GraphQLError("You must be logged in to perform this action.")

    @classmethod
    def get_payee(cls, user):
        """
        Fetches the Payee object associated with the authenticated user.
        """
        try:
            return Payee.objects.get(user=user)
        except Payee.DoesNotExist:
            logger.warning(f"Payee record not found for user {user.username}.")
            raise GraphQLError(
                "Payee record not found for the authenticated user."
            )

    @classmethod
    def validate_image_input(cls, image_file):
        """
        Validates the image file and handles errors.
        Uses the imported `validate_image` method.
        """
        try:
            validate_image(image_file)  # Reuse the imported method
        except ValidationError as e:
            logger.error(f"Image validation failed: {str(e)}")
            raise GraphQLError(f"Invalid image: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during image validation: {str(e)}")
            raise GraphQLError(
                "An unexpected error occurred while validating the image."
            )

    @classmethod
    def mutate(cls, root, info, **kwargs):
        """
        Entry point for the mutation.
        - Performs authorization checks.
        - Fetches the Payee object.
        - Executes the mutation logic.
        """
        cls.check_authorization(info.context)
        payee = cls.get_payee(info.context.user)

        # Ensure the authenticated user is the same as the Payee
        if payee.user != info.context.user:
            raise GraphQLError(
                "You are not authorized to perform this action.")

        return cls.perform_mutation(root, info, payee=payee, **kwargs)

    @classmethod
    def perform_mutation(cls, root, info, payee, **kwargs):
        """
        Abstract method to be implemented by subclasses.
        Contains the specific logic for the mutation.
        """
        raise NotImplementedError(
            "Subclasses must implement the `perform_mutation` method."
        )


class SetDarkMutation(BaseMutation):
    """
    This mutation allows the payee to Enable dark mode for a darker,
    low-light-friendly interface
    """

    class Arguments:
        is_dark_mode = graphene.Boolean(required=True)

    payee = graphene.Field(PayeeType)
    success = graphene.Boolean()
    message = graphene.String()

    @login_required
    def perform_mutation(cls, root, info, payee, **kwargs):
        is_dark_mode = kwargs.get("is_dark_mode")

        # Update the is_dark_mode field
        with transaction.atomic():
            payee.is_dark_mode = is_dark_mode
            payee.save(update_fields=["is_dark_mode"])

        return SetDarkMutation(
            success=True,
            message="Dark mode preference updated successfully.",
            payee=payee,
        )


class CreateBankDetailsAck(BaseMutation):
    """
    Handles the creation of a bank detail acknowledgment record.

    This mutation allows the user to provide their acknowledgment by uploading
    an image along with other required details. The acknowledgment details
    are then stored as part of the record creation process.
    """

    class Arguments:
        bank_detail_screenshot = Upload(required=True)
        is_approved = graphene.Boolean(required=False)
        correction_comments = graphene.String(required=False)

    bank_details_ack = graphene.Field(BankDetailsAckType)

    @staticmethod
    @login_required
    def perform_mutation(cls, root, info, payee, **kwargs):
        bank_detail_screenshot = kwargs.get("bank_detail_screenshot")
        is_approved = kwargs.get("is_approved", False)
        correction_comments = kwargs.get("correction_comments")

        # Validate and save image
        cls.validate_image_input(bank_detail_screenshot)

        # Save the BankDetailsAck instance
        bank_details_ack = BankDetailsAck.objects.create(
            payee=payee,
            bank_details_screenshot=bank_detail_screenshot,
            is_approved=is_approved,
            correction_comments=correction_comments,
        )
        return CreateBankDetailsAck(bank_details_ack=bank_details_ack)


class PayeesQuery(graphene.ObjectType):
    all_payees = graphene.List(PayeeType)
    all_bank_details = graphene.List(BankDetailsType)
    all_bank_details_ack = graphene.List(BankDetailsAckType)

    @staticmethod
    @login_required
    def resolve_all_payees(root, info):
        return Payee.objects.filter(user=info.context.user)

    @staticmethod
    @login_required
    def resolve_all_bank_details(root, info):
        return BankDetails.objects.filter(payee__user=info.context.user)

    @staticmethod
    @login_required
    def resolve_all_bank_details_ack(root, info):
        return BankDetailsAck.objects.filter(payee__user=info.context.user)


class PayeeMutation(graphene.ObjectType):
    create_bank_details_ack = CreateBankDetailsAck.Field()
    set_dark_mode_mutation = SetDarkMutation.Field()
