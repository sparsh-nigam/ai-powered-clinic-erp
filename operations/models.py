from django.db import models

from appointments.models import Appointment
from patients.models import Patient
from django.conf import settings
from django.utils import timezone


class PatientFile(models.Model):

    FILE_TYPE_CHOICES = [

        ('Prescription', 'Prescription'),

        ('Report', 'Report'),

        ('Document', 'Document'),

        ('Patient Photo', 'Patient Photo'),

    ]


    appointment = models.ForeignKey(

        Appointment,

        on_delete=models.CASCADE,

        related_name='patient_files',
        
        null = True,
        
        blank = True

    )


    file_type = models.CharField(

        max_length=30,

        choices=FILE_TYPE_CHOICES

    )
    
    custom_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )


    file = models.FileField(

        upload_to='patient_files/'

    )


    uploaded_at = models.DateTimeField(

        auto_now_add=True

    )


    def __str__(self):

        return f"{self.file_type} - {self.appointment}"
    
class BillingTransaction(models.Model):

    PAYMENT_STATUS = (

        ('Paid', 'Paid'),

        ('Pending', 'Pending'),

        ('Dues Pending', 'Dues Pending'),

        ('Refunded', 'Refunded'),

    )



    TRANSACTION_TYPES = (

        ('Consultation', 'Consultation'),

        ('Medicine', 'Medicine'),

        ('Procedure', 'Procedure'),

        ('Emergency', 'Emergency'),

        ('Refund', 'Refund'),

    )



    PAYMENT_MODES = (

        ('Cash', 'Cash'),

        ('UPI', 'UPI'),

        ('Card', 'Card'),

        ('Bank Transfer', 'Bank Transfer'),

    )



    patient = models.ForeignKey(

        Patient,

        on_delete=models.CASCADE

    )



    appointment = models.ForeignKey(

        Appointment,

        on_delete=models.SET_NULL,

        null=True,

        blank=True

    )
    
    billing_session = models.ForeignKey(

        'BillingSession',

        on_delete=models.CASCADE,

        related_name='transactions',

        null=True,

        blank=True

    )



    transaction_type = models.CharField(

        max_length=50,

        choices=TRANSACTION_TYPES

    )



    total_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    paid_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    pending_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    payment_status = models.CharField(

        max_length=30,

        choices=PAYMENT_STATUS,

        default='Pending'

    )

    is_void = models.BooleanField(

        default=False

    )

    payment_mode = models.CharField(

        max_length=30,

        choices=PAYMENT_MODES,

        blank=True,

        null=True

    )



    transaction_id = models.CharField(

        max_length=200,

        blank=True,

        null=True

    )



    payment_proof = models.ImageField(

        upload_to='billing_proofs/',

        blank=True,

        null=True

    )



    notes = models.TextField(

        blank=True,

        null=True

    )



    created_at = models.DateTimeField(

        auto_now_add=True

    )
    
    payment_received_at = models.DateTimeField(
        null=True,
        blank=True
    )



    def __str__(self):

        return f"{self.patient} - {self.transaction_type}"
    
class BillingItem(models.Model):

    billing_transaction = models.ForeignKey(

        BillingTransaction,

        on_delete=models.CASCADE,

        related_name='items'

    )



    item_name = models.CharField(

        max_length=255

    )



    quantity = models.PositiveIntegerField(

        default=1

    )



    price = models.DecimalField(

        max_digits=10,

        decimal_places=2

    )



    total_price = models.DecimalField(

        max_digits=10,

        decimal_places=2

    )



    created_at = models.DateTimeField(

        auto_now_add=True

    )



    def save(self, *args, **kwargs):

        self.total_price = (

            self.quantity * self.price

        )



        super().save(*args, **kwargs)



    def __str__(self):

        return self.item_name
    
class BillingSession(models.Model):

    SESSION_STATUS = (

        ('Active', 'Active'),

        ('Completed', 'Completed'),

        ('Due Pending', 'Due Pending'),

        ('Cancelled', 'Cancelled'),

    )



    VISIT_TYPE = (

        ('OPD', 'OPD'),

        ('Revisit', 'Revisit'),

        ('Emergency', 'Emergency'),

        ('Manual', 'Manual'),

    )
    


    session_number = models.CharField(

        max_length=100,

        unique=True

    )



    patient = models.ForeignKey(

        'patients.Patient',

        on_delete=models.CASCADE,

        related_name='billing_sessions'

    )



    appointment = models.ForeignKey(

        'appointments.Appointment',

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name='billing_sessions'

    )



    visit_type = models.CharField(

        max_length=50,

        choices=VISIT_TYPE,

        default='OPD'

    )



    session_status = models.CharField(

        max_length=50,

        choices=SESSION_STATUS,

        default='Active'

    )



    total_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    total_paid = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    total_due = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    discount_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    penalty_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    refund_amount = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )



    created_at = models.DateTimeField(

        auto_now_add=True

    )



    updated_at = models.DateTimeField(

        auto_now=True

    )



    def __str__(self):

        return self.session_number
    
    
    
class PatientCondition(models.Model):

    COMMON_CONDITIONS = [
        ('Diabetes', 'Diabetes'),
        ('Hypertension', 'Hypertension'),
        ('Kidney Disease', 'Kidney Disease'),
        ('Liver Disease', 'Liver Disease'),
        ('Thyroid', 'Thyroid'),
        ('Asthma', 'Asthma'),
        ('Heart Disease', 'Heart Disease'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='condition_records'
    )

    condition = models.CharField(
        max_length=100
    )

    is_custom = models.BooleanField(
        default=False
    )

    recall_enabled = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.condition}"
    
    
class AppointmentFollowUp(models.Model):

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='followup'
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='followup_records'
    )

    category = models.CharField(
        max_length=100
    )

    is_custom_category = models.BooleanField(
        default=False
    )
    
    followup_topic = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    followup_days = models.PositiveIntegerField()

    followup_due_date = models.DateField()

    reminder_enabled = models.BooleanField(
        default=True
    )

    reminder_count = models.PositiveIntegerField(
        default=0
    )

    last_reminder_sent = models.DateField(
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.category}"
    
class FollowUpCondition(models.Model):

    followup = models.ForeignKey(
        AppointmentFollowUp,
        on_delete=models.CASCADE,
        related_name='conditions'
    )

    condition_name = models.CharField(
        max_length=100
    )

    is_custom = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.condition_name
    
class MessageLog(models.Model):

    CHANNELS = (
        ('WhatsApp', 'WhatsApp'),
        ('SMS', 'SMS'),
    )

    MESSAGE_TYPES = (
        ('FollowUp', 'FollowUp'),
        ('ChronicRecall', 'ChronicRecall'),
        ('Manual', 'Manual'),
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNELS
    )

    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPES
    )

    message_content = models.TextField()

    sent_at = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=30,
        default='Pending'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    provider_response = models.TextField(
        null=True,
        blank=True
    )
    
    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.channel}"
    
class MessageTemplate(models.Model):

    TEMPLATE_TYPES = (

        ('FOLLOWUP_BEFORE', 'FOLLOWUP_BEFORE'),

        ('FOLLOWUP_DUE', 'FOLLOWUP_DUE'),

        ('FOLLOWUP_OVERDUE_1', 'FOLLOWUP_OVERDUE_1'),
        
        ('FOLLOWUP_OVERDUE_3', 'FOLLOWUP_OVERDUE_3'),
        
        ('FOLLOWUP_OVERDUE_7', 'FOLLOWUP_OVERDUE_7'),

        ('CHRONIC_30', 'CHRONIC_30'),
        
        ('CHRONIC_45', 'CHRONIC_45'),

        ('CHRONIC_60', 'CHRONIC_60'),

        ('CHRONIC_90', 'CHRONIC_90'),
        
        ('CHRONIC_105', 'CHRONIC_105'),

        ('CHRONIC_120', 'CHRONIC_120'),
        
        ('CHRONIC_150', 'CHRONIC_150'),
        
        ('CHRONIC_180', 'CHRONIC_180'),
        
        ('CHRONIC_210', 'CHRONIC_210'),
        
        ('CHRONIC_240', 'CHRONIC_240'),
        
        ('CHRONIC_270', 'CHRONIC_270'),
        
        ('CHRONIC_300', 'CHRONIC_300'),
        
        ('CHRONIC_330', 'CHRONIC_330'),
        
        ('CHRONIC_365', 'CHRONIC_365'),
        
    )

    name = models.CharField(
        max_length=100
    )

    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True
    )

    whatsapp_template = models.TextField()

    sms_template = models.TextField()

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name