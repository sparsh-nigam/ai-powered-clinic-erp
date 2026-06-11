from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class Patient(models.Model):
    Title_Choices = [
        ('Mr', 'Mr.'),
        ('Mrs', 'Mrs.'),
        ('Miss', 'Miss'),
        ('Dr', 'Dr.'),
        ('Mx', 'Mx.'),
    ]

    Gender_Choices = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('Oth', 'Other'),
    ]
    
    BloodGroup_Choices = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('Unknown','Unknown'),
    ]

    # CharFields should use blank=True, null=True for choice fields safely
    title = models.CharField(
        max_length=10,
        choices=Title_Choices,
        blank=True,
        null=True
    )

    patient_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    name = models.CharField(max_length=100)
    age = models.IntegerField()

    gender = models.CharField(
        max_length=10,
        choices=Gender_Choices,
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True, 
        default=''
    )

    address = models.TextField(
        blank=True, 
        default=''
    )

    disease = models.CharField(
        max_length=200,
        blank=True, 
        default=''
    )
    
    blood_group = models.CharField(
        max_length=8, 
        choices=BloodGroup_Choices, 
        blank=True, 
        default=''
    )
    
    allergies = models.CharField(
        max_length=255, 
        blank=True, 
        default='None known'
    )
    
    chronic_conditions = models.CharField(
        max_length=255, 
        blank=True, 
        default='None'
    )
    
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    appointment_date = models.DateField(
        blank=True,
        null=True
    )

    last_paid_consultation = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        # FIXED: Prevents printing "None John" if no title is selected
        if self.title:
            return f"{self.get_title_display()} {self.name}"
        return self.name

    @property
    def is_active_patient(self):
        if not self.last_paid_consultation:
            return False
        today = timezone.now().date()
        difference = today - self.last_paid_consultation
        return difference.days <= 6

    @property
    def revisit_valid_till(self):
        if not self.last_paid_consultation:
            return None
        return self.last_paid_consultation + timezone.timedelta(days=6)


@receiver(post_save, sender=Patient)
def generate_patient_id(sender, instance, created, **kwargs):
    if created and not instance.patient_id:
        # Generates ID based on the Primary Key
        instance.patient_id = f"PT{1000 + instance.id}"
        # FIXED: update_fields prevents a massive secondary database write
        instance.save(update_fields=['patient_id'])