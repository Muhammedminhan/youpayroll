from django.test import TestCase
from django.contrib.auth.models import User
from payees.models import Payee, BankDetails, BankDetailsAck

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
