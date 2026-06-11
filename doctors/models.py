from django.db import models
from django.conf import settings
# Create your models here.
class Doctor(models.Model):
    Specialization_Choicees=[
        ('Dermatologist','Dermatologist'),
        ('Cardiologist','Cardiologist'),
        ('Neurologist','Neurologist'),
        ('General','General Physician')
    ]
    Title_Choices=[('Dr','Dr.')]
    title=models.CharField(max_length=5,choices=Title_Choices)
    name=models.CharField(max_length=100)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_profile'
    )
    specialization=models.CharField(max_length=50,choices=Specialization_Choicees)
    phone=models.CharField(max_length=15)
    experience=models.IntegerField()
    
    def __str__(self):
        return f"{self.title} {self.name}"
#########################################################
class TransferRequest(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('Routine', 'Routine'),
        ('Urgent', 'Urgent'),
    ]

    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE
    )

    from_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='outgoing_transfers'
    )

    to_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='incoming_transfers'
    )

    reason = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='Routine'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.appointment} -> {self.to_doctor}"