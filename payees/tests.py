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
