from django.db import models
from appointments.models import Appointment


class ConsultationRecord(models.Model):

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Completed', 'Completed'),
    ]

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='consultation_record'
    )

    chief_complaint = models.TextField(
        blank=True
    )

    diagnosis = models.TextField(
        blank=True
)

    clinical_notes = models.TextField(
        blank=True
    )

    advice = models.TextField(
        blank=True
    )

    followup_instruction = models.CharField(
        max_length=255,
        blank=True
    )

    expected_followup_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Draft'
    )

    completed_at = models.DateTimeField(
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
        return f"Consultation - {self.appointment.id}"
    
class TreatmentItem(models.Model):

    ITEM_TYPE_CHOICES = [
        ('Medicine', 'Medicine'),
        ('Test', 'Test'),
        ('Procedure', 'Procedure'),
        ('Therapy', 'Therapy'),
        ('Instruction', 'Instruction'),
    ]

    consultation_record = models.ForeignKey(
        ConsultationRecord,
        on_delete=models.CASCADE,
        related_name='treatment_items'
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES
    )

    name = models.CharField(
        max_length=255
    )

    dosage = models.CharField(
        max_length=100,
        blank=True
    )

    duration = models.CharField(
        max_length=100,
        blank=True
    )

    morning_before_breakfast = models.BooleanField(
        default=False
    )

    morning_after_breakfast = models.BooleanField(
        default=False
    )

    afternoon_before_lunch = models.BooleanField(
        default=False
    )

    afternoon_after_lunch = models.BooleanField(
        default=False
    )

    evening_before_snack = models.BooleanField(
        default=False
    )

    evening_after_snack = models.BooleanField(
        default=False
    )

    night_before_dinner = models.BooleanField(
        default=False
    )

    night_after_dinner = models.BooleanField(
        default=False
    )

    timing_guidance = models.TextField(
        blank=True
    )

    instructions = models.TextField(
        blank=True
    )
    
    display_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.item_type} - {self.name}"