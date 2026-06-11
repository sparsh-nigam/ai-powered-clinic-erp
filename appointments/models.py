from django.db import models
from patients.models import Patient
from doctors.models import Doctor

class Appointment(models.Model):
    Status_Choices=[
        ('Pending','Pending'),
        ('Completed','Completed'),
        ('In Consultation','In Consultation'),
        ('Transfer Requested','Transfer Requested'),
        ('Cancelled','Cancelled'),
        ('Expired', 'Expired'),
    ]
    
    patient=models.ForeignKey(Patient,on_delete=models.CASCADE)
    doctor=models.ForeignKey(Doctor,on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    appointment_date=models.DateField()
    appointment_time=models.TimeField()
    
    daily_token = models.IntegerField(
        null=True,
        blank=True
    )
    status=models.CharField(max_length=20,choices=Status_Choices,default='Pending')

    Payment_Status_Choices = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Waived',  'Waived'),
        ('Dues Pending', 'Dues Pending'),
    ]

    Payment_Mode_Choices = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Card', 'Card'),
    ]

    updated_at = models.DateTimeField(
        auto_now=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    notes=models.TextField(blank=True,null=True)
    
    payment_status = models.CharField(
        max_length=20,
        choices=Payment_Status_Choices,
        default='Pending'
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=Payment_Mode_Choices,
        null=True,
        blank=True
    )

    amount_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # ADDED: Safe File field reference to store the incoming consultation transaction proof
    payment_proof = models.FileField(
        upload_to='appointment_proofs/',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"{self.patient} -> {self.doctor}"