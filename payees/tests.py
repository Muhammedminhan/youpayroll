from importlib import import_module

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from unittest.mock import patch
from payees.admin import PayeeAdmin
from payees.models import Payee, BankDetails, BankDetailsAck

choose_bank_details_keeper = import_module(
    'payees.migrations.0007_bankdetails_unique_payee'
).choose_bank_details_keeper


class PayeeAdminZohoSyncTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password',
        )
        self.payee_admin = PayeeAdmin(Payee, admin.site)

    def test_save_model_queues_fetch_details_task(self):
        request = self.factory.post('/admin/payees/payee/add/')
        request.user = self.admin_user
        payee_user = User.objects.create_user(username='payee_user')
        payee = Payee(hrm_id='HR123', user=payee_user)

        with patch('payees.admin.fetch_details.delay') as mock_delay, \
                patch.object(self.payee_admin, 'message_user') as mock_message_user:
            self.payee_admin.save_model(request, payee, form=None, change=False)

        mock_delay.assert_called_once_with('HR123')
        mock_message_user.assert_called_once_with(
            request,
            "Queued Zoho detail sync.",
            level=messages.INFO,
        )

    def test_fetch_from_zoho_action_queues_fetch_details_tasks(self):
        request = self.factory.post('/admin/payees/payee/')
        request.user = self.admin_user
        payee_user_1 = User.objects.create_user(username='payee_user_1')
        payee_user_2 = User.objects.create_user(username='payee_user_2')
        payee_1 = Payee.objects.create(hrm_id='HR123', user=payee_user_1)
        payee_2 = Payee.objects.create(hrm_id='HR456', user=payee_user_2)
        queryset = Payee.objects.filter(id__in=[payee_1.id, payee_2.id]).order_by('hrm_id')

        with patch('payees.admin.fetch_details.delay') as mock_delay, \
                patch.object(self.payee_admin, 'message_user') as mock_message_user:
            self.payee_admin.fetch_from_zoho_action(request, queryset)

        self.assertEqual(mock_delay.call_count, 2)
        mock_delay.assert_any_call('HR123')
        mock_delay.assert_any_call('HR456')
        mock_message_user.assert_called_once_with(
            request,
            "Queued Zoho detail sync for 2 payees.",
        )

    def test_zoho_sync_uses_admin_action_not_change_form_button(self):
        self.assertIn('fetch_from_zoho_action', self.payee_admin.actions)
        self.assertNotIn('fetch_zoho_button', self.payee_admin.readonly_fields)

class BankDetailsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.payee = Payee.objects.create(user=self.user, hrm_id='HR123')
        self.bank_details = BankDetails.objects.create(
            payee=self.payee,
            bank_name='Test Bank',
            account_no='1234567890',
            payee_acknowledgement=True
        )

    def test_bank_details_change_resets_acknowledgement(self):
        """
        Verifies that any mutation on tracked fields resets payee_acknowledgement to False.
        Note: This is handled atomically inside BankDetails.save() rather than payees/signals.py.
        """
        # Update bank name
        self.bank_details.bank_name = 'New Bank'
        self.bank_details.save()
        
        self.bank_details.refresh_from_db()
        self.assertFalse(self.bank_details.payee_acknowledgement)

    def test_bank_details_change_deletes_stale_acknowledgements(self):
        import io
        from PIL import Image

        old_image = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(old_image, format='PNG')
        old_image.seek(0)
        new_image = io.BytesIO()
        Image.new('RGB', (10, 10), color='black').save(new_image, format='PNG')
        new_image.seek(0)

        BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=SimpleUploadedFile(
                name='old_ack.png',
                content=old_image.read(),
                content_type='image/png',
            ),
        )

        self.bank_details.ifsc_code = 'NEWIFSC123'
        self.bank_details.save()

        self.bank_details.refresh_from_db()
        self.assertEqual(self.bank_details.ifsc_code, 'NEWIFSC123')
        self.assertFalse(self.bank_details.payee_acknowledgement)
        self.assertFalse(BankDetailsAck.objects.filter(bank_details=self.bank_details).exists())

        BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=SimpleUploadedFile(
                name='new_ack.png',
                content=new_image.read(),
                content_type='image/png',
            ),
        )
        self.assertEqual(BankDetailsAck.objects.filter(bank_details=self.bank_details).count(), 1)

    def test_bank_details_change_preserves_acknowledgements_when_save_fails(self):
        import io
        from PIL import Image

        image = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(image, format='PNG')
        image.seek(0)

        ack = BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=SimpleUploadedFile(
                name='old_ack.png',
                content=image.read(),
                content_type='image/png',
            ),
            is_approved=True,
        )

        self.bank_details.ifsc_code = 'NEWIFSC123'

        with self.assertRaises(ValueError):
            self.bank_details.save(update_fields=['ifsc_code', 'not_a_field'])

        self.bank_details.refresh_from_db()
        self.assertTrue(BankDetailsAck.objects.filter(id=ack.id).exists())
        self.assertNotEqual(self.bank_details.ifsc_code, 'NEWIFSC123')
        self.assertTrue(self.bank_details.payee_acknowledgement)

    def test_non_tracked_field_does_not_reset_acknowledgement(self):
        # account_holder_name is tracked, but let's assume we update nothing
        self.bank_details.save()
        self.assertTrue(self.bank_details.payee_acknowledgement)

    def test_payee_email_syncs_with_user_email(self):
        self.payee.email = 'payee@example.com'
        self.payee.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'payee@example.com')

        self.user.email = 'updated@example.com'
        self.user.save()

        self.payee.refresh_from_db()
        self.assertEqual(self.payee.email, 'updated@example.com')

    def test_payee_save_validates_email_before_syncing_user_email(self):
        self.user.email = 'old@example.com'
        self.user.save()
        self.payee.email = 'old@example.com'
        self.payee.save()

        self.payee.email = 'not-an-email'

        with self.assertRaises(ValidationError):
            self.payee.save()

        self.user.refresh_from_db()
        self.payee.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertEqual(self.payee.email, 'old@example.com')

    def test_payee_save_rolls_back_user_email_sync_when_payee_save_fails(self):
        self.user.email = 'old@example.com'
        self.user.save()
        self.payee.email = 'old@example.com'
        self.payee.save()

        other_user = User.objects.create_user(username='other_user')
        Payee.objects.create(user=other_user, hrm_id='HR999')

        self.payee.email = 'new@example.com'
        self.payee.hrm_id = 'HR999'

        with self.assertRaises(IntegrityError):
            self.payee.save()

        self.user.refresh_from_db()
        self.payee.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertEqual(self.payee.email, 'old@example.com')


from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile


class BankDetailAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='bank_detail_user', password='password')
        self.payee = Payee.objects.create(user=self.user, hrm_id='HRBD1', full_name='Bank Detail User')
        self.client.force_authenticate(user=self.user)

    def test_create_then_post_updates_current_bank_details(self):
        create_response = self.client.post(
            '/api/payees/bank-details/',
            {
                'bank_name': 'First Bank',
                'account_no': '1234567890',
                'account_holder_name': 'Bank Detail User',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)

        update_response = self.client.post(
            '/api/payees/bank-details/',
            {
                'bank_name': 'Updated Bank',
                'account_no': '9876543210',
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(BankDetails.objects.filter(payee=self.payee).count(), 1)

        bank_details = BankDetails.objects.get(payee=self.payee)
        self.assertEqual(bank_details.bank_name, 'Updated Bank')
        self.assertEqual(bank_details.account_no, '9876543210')

    def test_create_returns_201_and_post_update_returns_200(self):
        create_response = self.client.post('/api/payees/bank-details/', {'bank_name': 'First Bank'}, format='json')
        update_response = self.client.post('/api/payees/bank-details/', {'bank_name': 'Updated Bank'}, format='json')

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(update_response.status_code, 200)

    def test_bank_details_are_unique_per_payee_at_database_level(self):
        BankDetails.objects.create(payee=self.payee, bank_name='First Bank')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BankDetails.objects.create(payee=self.payee, bank_name='Duplicate Bank')

    def test_patch_corrects_bank_details_and_resets_acknowledgement(self):
        bank_details = BankDetails.objects.create(
            payee=self.payee,
            bank_name='Original Bank',
            account_no='1234567890',
            payee_acknowledgement=True,
        )

        response = self.client.patch(
            f'/api/payees/bank-details/{bank_details.id}/',
            {'bank_name': 'Corrected Bank'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        bank_details.refresh_from_db()
        self.assertEqual(bank_details.bank_name, 'Corrected Bank')
        self.assertFalse(bank_details.payee_acknowledgement)

    def test_delete_bank_details_is_not_allowed(self):
        bank_details = BankDetails.objects.create(
            payee=self.payee,
            bank_name='Original Bank',
            account_no='1234567890',
        )

        response = self.client.delete(f'/api/payees/bank-details/{bank_details.id}/')

        self.assertEqual(response.status_code, 405)
        self.assertTrue(BankDetails.objects.filter(id=bank_details.id).exists())


class BankDetailsMigrationTest(TestCase):
    def test_duplicate_collapse_preserves_acknowledgement_and_merges_fields(self):
        bank_details = [
            {
                'id': 5,
                'payee_acknowledgement': True,
                'bank_name': 'Audited Bank',
                'account_no': None,
                'account_holder_name': 'Audited Holder',
                'account_type': None,
                'ifsc_code': 'AUDITIFSC',
                'micr_code': None,
                'swift_code': None,
                'branch_address': None,
            },
            {
                'id': 10,
                'payee_acknowledgement': False,
                'bank_name': None,
                'account_no': '9876543210',
                'account_holder_name': None,
                'account_type': 'Savings',
                'ifsc_code': None,
                'micr_code': 'MICR001',
                'swift_code': 'SWIFT001',
                'branch_address': 'Merged Branch',
            },
        ]
        acknowledgements = [
            {'id': 100, 'bank_details_id': 5, 'is_approved': True},
            {'id': 101, 'bank_details_id': 10, 'is_approved': False},
        ]

        keeper_id, keeper_ack_id, ack_ids_to_delete, merged_values = choose_bank_details_keeper(
            bank_details,
            acknowledgements,
        )

        self.assertEqual(keeper_id, 5)
        self.assertEqual(keeper_ack_id, 100)
        self.assertEqual(ack_ids_to_delete, [101])
        self.assertTrue(merged_values['payee_acknowledgement'])
        self.assertEqual(merged_values['bank_name'], 'Audited Bank')
        self.assertEqual(merged_values['account_no'], '9876543210')
        self.assertEqual(merged_values['ifsc_code'], 'AUDITIFSC')
        self.assertEqual(merged_values['branch_address'], 'Merged Branch')


class BankDetailAcknowledgementAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='payee_user', password='password')
        self.payee = Payee.objects.create(user=self.user, hrm_id='HR456', full_name='John Doe')
        self.client.force_authenticate(user=self.user)
        
        self.bank_details = BankDetails.objects.create(
            payee=self.payee,
            bank_name='Standard Bank',
            account_no='987654321',
            payee_acknowledgement=False
        )
        
        import io
        from PIL import Image
        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        self.dummy_image = SimpleUploadedFile(
            name='test_image.png',
            content=img_buffer.read(),
            content_type='image/png'
        )

    def test_create_acknowledgement_requires_explicit_bank_details(self):
        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {'bank_details_screenshot': self.dummy_image},
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("This field is required", response.content.decode())

    def test_create_acknowledgement_with_explicit_bank_details(self):
        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {
                'bank_details_screenshot': self.dummy_image,
                'bank_details': self.bank_details.id
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['bank_details'], self.bank_details.id)

    def test_create_acknowledgement_wrong_owner_rejected(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_payee = Payee.objects.create(user=other_user, hrm_id='HR789')
        other_bank_details = BankDetails.objects.create(
            payee=other_payee,
            bank_name='Other Bank',
            account_no='1111111'
        )
        
        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {
                'bank_details_screenshot': self.dummy_image,
                'bank_details': other_bank_details.id
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("The specified bank details do not belong to this payee", response.content.decode())

    def test_create_acknowledgement_duplicate_bank_details_rejected(self):
        BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=self.dummy_image,
        )

        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {
                'bank_details_screenshot': self.dummy_image,
                'bank_details': self.bank_details.id,
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Bank details have already been acknowledged", response.content.decode())

    def test_create_acknowledgement_integrity_error_returns_validation_error(self):
        BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=self.dummy_image,
        )
        import io
        from PIL import Image

        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        fresh_image = SimpleUploadedFile(
            name='race_image.png',
            content=img_buffer.read(),
            content_type='image/png'
        )

        with patch(
            'payees.serializers.BankDetailAcknowledgementSerializer.validate_bank_details',
            new=lambda serializer, value: value,
        ):
            response = self.client.post(
                '/api/payees/bank-acknowledgements/',
                {
                    'bank_details_screenshot': fresh_image,
                    'bank_details': self.bank_details.id,
                },
                format='multipart'
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Bank details have already been acknowledged", response.content.decode())

    def test_acknowledgement_is_unique_per_bank_details(self):
        BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=self.dummy_image,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BankDetailsAck.objects.create(
                    payee=self.payee,
                    bank_details=self.bank_details,
                    bank_details_screenshot=self.dummy_image,
                )

    def test_acknowledgement_requires_bank_details_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BankDetailsAck.objects.create(
                    payee=self.payee,
                    bank_details_screenshot='legacy_ack.png',
                )

    def test_approval_marks_bank_details_as_acknowledged(self):
        # Create an unapproved acknowledgement
        ack = BankDetailsAck.objects.create(
            payee=self.payee,
            bank_details=self.bank_details,
            bank_details_screenshot=self.dummy_image
        )
        self.assertFalse(self.bank_details.payee_acknowledgement)
        
        # Approve it
        ack.is_approved = True
        ack.save()
        
        self.bank_details.refresh_from_db()
        self.assertTrue(self.bank_details.payee_acknowledgement)

        ack.is_approved = False
        ack.save()

        self.bank_details.refresh_from_db()
        self.assertFalse(self.bank_details.payee_acknowledgement)


class BankDetailsAckGraphQLTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='graphql_payee', password='password')
        self.payee = Payee.objects.create(user=self.user, hrm_id='HRGQL', full_name='GraphQL Payee')
        self.bank_details = BankDetails.objects.create(
            payee=self.payee,
            bank_name='GraphQL Bank',
            account_no='1234567890',
            payee_acknowledgement=False
        )

    def test_create_bank_details_ack_forces_is_approved_false(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from graphene.test import Client
        from youpayroll.schema import schema

        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        screenshot = SimpleUploadedFile(
            name='graphql_ack.png',
            content=img_buffer.read(),
            content_type='image/png'
        )

        mutation = """
        mutation CreateAck($screenshot: Upload!, $bankDetailsId: ID!) {
            createBankDetailsAck(
                bankDetailScreenshot: $screenshot,
                bankDetailsId: $bankDetailsId,
                isApproved: true
            ) {
                bankDetailsAck {
                    isApproved
                }
            }
        }
        """

        class DummyContext:
            user = self.user

        result = Client(schema).execute(
            mutation,
            variable_values={
                'screenshot': screenshot,
                'bankDetailsId': str(self.bank_details.id),
            },
            context=DummyContext(),
        )

        self.assertNotIn('errors', result)
        self.assertFalse(result['data']['createBankDetailsAck']['bankDetailsAck']['isApproved'])

        ack = BankDetailsAck.objects.get(payee=self.payee)
        self.assertEqual(ack.bank_details, self.bank_details)
        self.assertFalse(ack.is_approved)
        self.bank_details.refresh_from_db()
        self.assertFalse(self.bank_details.payee_acknowledgement)

    def test_create_bank_details_ack_rejects_bank_details_owned_by_another_payee(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from graphene.test import Client
        from youpayroll.schema import schema

        other_user = User.objects.create_user(username='other_graphql_payee')
        other_payee = Payee.objects.create(user=other_user, hrm_id='HROTHER')
        other_bank_details = BankDetails.objects.create(payee=other_payee)

        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        screenshot = SimpleUploadedFile(
            name='graphql_ack_wrong_owner.png',
            content=img_buffer.read(),
            content_type='image/png'
        )

        mutation = """
        mutation CreateAck($screenshot: Upload!, $bankDetailsId: ID!) {
            createBankDetailsAck(
                bankDetailScreenshot: $screenshot,
                bankDetailsId: $bankDetailsId
            ) {
                bankDetailsAck {
                    isApproved
                }
            }
        }
        """

        class DummyContext:
            user = self.user

        result = Client(schema).execute(
            mutation,
            variable_values={
                'screenshot': screenshot,
                'bankDetailsId': str(other_bank_details.id),
            },
            context=DummyContext(),
        )

        self.assertIn('errors', result)
        self.assertIn(
            'The specified bank details do not belong to this payee.',
            str(result['errors'][0]),
        )

    def test_create_bank_details_ack_requires_bank_details_id_argument(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from graphene.test import Client
        from youpayroll.schema import schema

        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        screenshot = SimpleUploadedFile(
            name='graphql_ack_missing_bank_details.png',
            content=img_buffer.read(),
            content_type='image/png'
        )

        mutation = """
        mutation CreateAck($screenshot: Upload!) {
            createBankDetailsAck(bankDetailScreenshot: $screenshot) {
                bankDetailsAck {
                    isApproved
                }
            }
        }
        """

        class DummyContext:
            user = self.user

        result = Client(schema).execute(
            mutation,
            variable_values={'screenshot': screenshot},
            context=DummyContext(),
        )

        self.assertIn('errors', result)
        self.assertIn('bankDetailsId', str(result['errors'][0]))


class ValidateImageTest(TestCase):
    def test_valid_image_passes(self):
        import io
        from PIL import Image
        from payees.upload_helpers import validate_image
        
        img_buffer = io.BytesIO()
        Image.new('RGB', (10, 10), color='white').save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Should not raise ValidationError
        validate_image(img_buffer)
        self.assertEqual(img_buffer.tell(), 0)

    def test_invalid_image_rejected_without_leaking_details(self):
        import io
        from payees.upload_helpers import validate_image
        
        bad_buffer = io.BytesIO(b'completely invalid image content')
        
        with self.assertRaises(ValidationError) as ctx:
            validate_image(bad_buffer)
            
        self.assertEqual(str(ctx.exception), "['The uploaded file is not a valid image.']")
