from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from auditlog.registry import auditlog
from django.utils import timezone
import datetime

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    consultant_id = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], blank=True)
    dob = models.DateField(null=True, blank=True)
    
    # Contract Details
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    consultant_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Reporting
    reporting_to_name = models.CharField(max_length=100, blank=True)
    reporting_to_role = models.CharField(max_length=100, blank=True)
    
    profile_picture = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signals to auto-create Profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    # Only sync on creation. Unconditional save() on every User.save() would
    # trigger an extra Profile write on every email update/bulk update in a loop.
    if created and hasattr(instance, 'profile'):
        instance.profile.save()

class Payslip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payslips')
    month = models.CharField(max_length=20) # e.g., "October"
    year = models.IntegerField()
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2)
    reimbursement = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    take_home = models.DecimalField(max_digits=10, decimal_places=2)
    file = models.FileField(upload_to='payslips/', null=True, blank=True)
    tax_worksheet = models.FileField(upload_to='tax_worksheets/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip - {self.user.username} - {self.month} {self.year}"

class Document(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UPLOADED', 'Uploaded'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    file = models.FileField(upload_to='documents/', null=True, blank=True)
    admin_feedback = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class AdminNotification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class WikiCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Wiki Categories"

    def __str__(self):
        return self.name

class WikiPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField() # Markdown content
    category = models.ForeignKey(WikiCategory, on_delete=models.SET_NULL, null=True, related_name='pages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='INFO') # e.g., 'ACTION_REQUIRED', 'INFO'
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

USER_PROFILE_COMPLETION_FIELDS = (
    ('first_name', 'First name'),
    ('last_name', 'Last name'),
)

PROFILE_COMPLETION_FIELDS = (
    ('designation', 'Designation'),
    ('gender', 'Gender'),
    ('dob', 'Date of birth'),
)


def get_missing_profile_fields(profile):
    missing_fields = []
    user = profile.user

    for field_name, label in USER_PROFILE_COMPLETION_FIELDS:
        if not getattr(user, field_name):
            missing_fields.append(label)

    for field_name, label in PROFILE_COMPLETION_FIELDS:
        if not getattr(profile, field_name):
            missing_fields.append(label)

    return missing_fields


def ensure_profile_completion_notification(profile):
    missing_fields = get_missing_profile_fields(profile)
    if not missing_fields:
        return

    recent_threshold = timezone.now() - datetime.timedelta(minutes=5)
    has_unread = UserNotification.objects.filter(
        user=profile.user,
        notification_type='ACTION_REQUIRED',
        is_read=False
    ).exists()

    was_recently_sent = UserNotification.objects.filter(
        user=profile.user,
        notification_type='ACTION_REQUIRED',
        created_at__gt=recent_threshold
    ).exists()

    if has_unread or was_recently_sent:
        return

    UserNotification.objects.create(
        user=profile.user,
        notification_type='ACTION_REQUIRED',
        is_read=False,
        title="Complete your profile",
        message=(
            "Please complete the missing profile details: "
            f"{', '.join(missing_fields)}."
        )
    )
auditlog.register(Profile)
auditlog.register(Payslip)
auditlog.register(Document)
auditlog.register(WikiPage)
