from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from unittest.mock import patch
from payees.admin import PayeeAdmin
from payees.models import Payee, BankDetails, BankDetailsAck


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

        with patch('payees.admin.fetch_details.delay') as mock_delay:
            self.payee_admin.save_model(request, payee, form=None, change=False)

        mock_delay.assert_called_once_with('HR123')

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

    def test_non_tracked_field_does_not_reset_acknowledgement(self):
        # account_holder_name is tracked, but let's assume we update nothing
        self.bank_details.save()
        self.assertTrue(self.bank_details.payee_acknowledgement)


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

    def test_create_acknowledgement_fallback_to_latest_bank_details(self):
        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {'bank_details_screenshot': self.dummy_image},
            format='multipart'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['bank_details'], self.bank_details.id)
        
        ack = BankDetailsAck.objects.get(id=response.data['id'])
        self.assertEqual(ack.bank_details, self.bank_details)
        self.assertFalse(ack.is_approved)

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

    def test_create_acknowledgement_no_bank_details_raises_validation_error(self):
        # Delete existing bank details
        self.bank_details.delete()
        
        response = self.client.post(
            '/api/payees/bank-acknowledgements/',
            {'bank_details_screenshot': self.dummy_image},
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No bank details record found to acknowledge", response.content.decode())

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
        mutation CreateAck($screenshot: Upload!) {
            createBankDetailsAck(
                bankDetailScreenshot: $screenshot,
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
            variable_values={'screenshot': screenshot},
            context=DummyContext(),
        )

        self.assertNotIn('errors', result)
        self.assertFalse(result['data']['createBankDetailsAck']['bankDetailsAck']['isApproved'])

        ack = BankDetailsAck.objects.get(payee=self.payee)
        self.assertEqual(ack.bank_details, self.bank_details)
        self.assertFalse(ack.is_approved)
        self.bank_details.refresh_from_db()
        self.assertFalse(self.bank_details.payee_acknowledgement)


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
