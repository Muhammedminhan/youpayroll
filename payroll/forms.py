import datetime

from django import forms

from .models import PayRunStatusChoices, PayRun


class PayRunForm(forms.ModelForm):
    """
    This PayRunForm manages PayRun instances, allowing editing of month and
    year fields only for the initial instance. For subsequent entries, these
    fields are set to read-only based on the status of the latest PayRun.
    The form ensures the month value is restricted to the range of 1 to 12
    """
    class Meta:
        model = PayRun
        fields = ['month', 'year', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk is not None:
            """
            If the PayRun object exists, make 'month' and 'year' fields 
            read-only
            """
            self.fields['month'].widget.attrs['readonly'] = 'readonly'
            self.fields['year'].widget.attrs['readonly'] = 'readonly'

        else:
            if PayRun.objects.exists():
                latest_payrun = PayRun.objects.latest('created_at')
                next_month = latest_payrun.month + 1
                next_year = latest_payrun.year

                # Adjust year if month overflows
                if next_month > 12:
                    next_month = 1
                    next_year += 1

                if latest_payrun.status == PayRunStatusChoices.APPROVED:
                    self.fields['month'].initial = next_month
                    self.fields['year'].initial = next_year

                    # Make the month and year fields read-only
                    self.fields['month'].widget.attrs['readonly'] = 'readonly'
                    self.fields['year'].widget.attrs['readonly'] = 'readonly'

                elif latest_payrun.status == PayRunStatusChoices.REJECTED:
                    self.fields['month'].initial = latest_payrun.month
                    self.fields['year'].initial = latest_payrun.year

                    # Make the month and year fields read-only
                    self.fields['month'].widget.attrs['readonly'] = 'readonly'
                    self.fields['year'].widget.attrs['readonly'] = 'readonly'

            else:
                # For the initial PayRun, autofill current month and year
                current_date = datetime.date.today()
                self.fields['month'].initial = current_date.month
                self.fields['year'].initial = current_date.year

                # Allow editing for the first PayRun instance
                self.fields['month'].widget.attrs.pop('readonly', None)
                self.fields['year'].widget.attrs.pop('readonly', None)

            # Ensure the month field accepts values in the range of 1 to 12.
            self.fields['month'].widget.attrs['min'] = 1
            self.fields['month'].widget.attrs['max'] = 12
