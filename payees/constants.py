RESTRICTED_PAYEE_GROUPS = ['PAYEE']

YGG_EMAIL_DOMAIN = "yougotagift.com"

JANUARY = 1
FEBRUARY = 2
MARCH = 3
APRIL = 4
MAY = 5
JUNE = 6
JULY = 7
AUGUST = 8
SEPTEMBER = 9
OCTOBER = 10
NOVEMBER = 11
DECEMBER = 12
MONTH_CHOICES = [
    (JANUARY, 'January'),
    (FEBRUARY, 'February'),
    (MARCH, 'March'),
    (APRIL, 'April'),
    (MAY, 'May'),
    (JUNE, 'June'),
    (JULY, 'July'),
    (AUGUST, 'August'),
    (SEPTEMBER, 'September'),
    (OCTOBER, 'October'),
    (NOVEMBER, 'November'),
    (DECEMBER, 'December'),
]

TDS_LEGAL_NAME_CHOICES = [
    ("technical-consultants", "Technical Consultants"),
    ("professional-consultant", "Professional Consultant"),
    ("employment", "Employment"),
    ("apprentices", "Apprentices"),
]

STATUS_CHOICES = [
    ('active', 'Active'),
    ('removed', 'Removed'),
    ('disengaged', 'Disengaged')
]
PAYEE_STATUS_HELP_TEXT = ('Select the current status of the payee. '
                          '"Active" for currently working, '
                          '"Removed" for those who have been removed from '
                          'their position, and '
                          '"Disengaged" for those who are no longer engaged '
                          'with the company.')
