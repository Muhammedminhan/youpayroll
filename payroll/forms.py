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

        # Ensure the month field accepts values in the range of 1 to 12.
        self.fields['month'].widget.attrs['min'] = 1
        self.fields['month'].widget.attrs['max'] = 12

        if self.instance.pk is not None:
            # Existing record: lock month and year from editing
            self.fields['month'].widget.attrs['readonly'] = 'readonly'
            self.fields['year'].widget.attrs['readonly'] = 'readonly'

        elif PayRun.objects.exists():
            # New record when prior PayRuns exist: auto-suggest next period
            # Order by year/month to find the chronologically latest run
            latest_payrun = PayRun.objects.order_by('-year', '-month').first()
            next_month = latest_payrun.month + 1
            next_year = latest_payrun.year

            # Adjust year if month overflows
            if next_month > 12:
                next_month = 1
                next_year += 1

            if latest_payrun.status == PayRunStatusChoices.APPROVED:
                self.fields['month'].initial = next_month
                self.fields['year'].initial = next_year
                self.fields['month'].widget.attrs['readonly'] = 'readonly'
                self.fields['year'].widget.attrs['readonly'] = 'readonly'

            elif latest_payrun.status == PayRunStatusChoices.REJECTED:
                self.fields['month'].initial = latest_payrun.month
                self.fields['year'].initial = latest_payrun.year
                self.fields['month'].widget.attrs['readonly'] = 'readonly'
                self.fields['year'].widget.attrs['readonly'] = 'readonly'

            else:
                # Default for other statuses (DUE, IN_PROGRESS, COMPLETED)
                # Allow editing but suggest next period
                self.fields['month'].initial = next_month
                self.fields['year'].initial = next_year

        else:
            # First-ever PayRun: autofill current month/year and allow editing
            current_date = datetime.date.today()
            self.fields['month'].initial = current_date.month
            self.fields['year'].initial = current_date.year

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk:
            # Enforce immutability for month and year after creation
            if cleaned_data.get('month') != self.instance.month:
                self.add_error('month', "Month cannot be changed after creation.")
            if cleaned_data.get('year') != self.instance.year:
                self.add_error('year', "Year cannot be changed after creation.")
        return cleaned_data
