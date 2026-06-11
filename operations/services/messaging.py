from operations.models import (
    MessageTemplate,
    MessageLog
)
from datetime import timedelta
from django.utils import timezone
from operations.models import AppointmentFollowUp
from operations.models import PatientCondition
from appointments.models import Appointment
from patients.models import Patient

def create_message_log(
    patient,
    channel,
    message_type,
    message_content,
    created_by=None
):

    return MessageLog.objects.create(

        patient=patient,

        channel=channel,

        message_type=message_type,

        message_content=message_content,

        status='Pending',

        created_by=created_by
    )
    
    
def generate_followup_logs():

    today = timezone.localdate()

    followups = AppointmentFollowUp.objects.filter(
        reminder_enabled=True
    )

    generated = 0

    for followup in followups:

        due_date = followup.followup_due_date

        if due_date == today + timedelta(days=1):

            template_type = 'FOLLOWUP_BEFORE'

        elif due_date == today:

            template_type = 'FOLLOWUP_DUE'

        elif due_date == today - timedelta(days=1):

            template_type = 'FOLLOWUP_OVERDUE_1'

        elif due_date == today - timedelta(days=3):

            template_type = 'FOLLOWUP_OVERDUE_3'

        elif due_date == today - timedelta(days=7):

            template_type = 'FOLLOWUP_OVERDUE_7'

        else:
            continue

        template = MessageTemplate.objects.get(
            template_type=template_type
        )

        message = (
            template.whatsapp_template
            .replace(
                '{patient_name}',
                followup.patient.name
            )
            .replace(
                '{due_date}',
                str(followup.followup_due_date)
            )
        )
        
        existing_log = MessageLog.objects.filter(
            patient=followup.patient,
            message_type='FollowUp',
            sent_at__date=today
        ).exists()

        if existing_log:
            continue
        
        
        create_message_log(
            patient=followup.patient,
            channel='WhatsApp',
            message_type='FollowUp',
            message_content=message
        )

        generated += 1

    return generated

def generate_chronic_recall_logs():

    today = timezone.localdate()

    generated = 0

    recall_days = [
        30,
        45,
        60,
        90,
        105,
        120,
        150,
        180,
        210,
        240,
        270,
        300,
        330,
        365
    ]

    patients = Patient.objects.filter(
        condition_records__recall_enabled=True
    ).distinct()

    for patient in patients:

        last_visit = Appointment.objects.filter(
            patient=patient,
            status='Completed'
        ).order_by(
            '-appointment_date'
        ).first()

        if not last_visit:
            continue

        days_since_visit = (
            today - last_visit.appointment_date
        ).days

        if days_since_visit not in recall_days:
            continue

        template_type = (
            f'CHRONIC_{days_since_visit}'
        )

        template = MessageTemplate.objects.get(
            template_type=template_type
        )

        conditions = PatientCondition.objects.filter(
            patient=patient,
            recall_enabled=True
        )

        condition_names = ", ".join(
            conditions.values_list(
                'condition',
                flat=True
            )
        )

        message = (
            template.whatsapp_template
            .replace(
                '{patient_name}',
                patient.name
            )
            .replace(
                '{conditions}',
                condition_names
            )
        )
        
        existing_log = MessageLog.objects.filter(
            patient=patient,
            message_type='ChronicRecall',
            sent_at__date=today
        ).exists()

        if existing_log:
            continue

        create_message_log(
            patient=patient,
            channel='WhatsApp',
            message_type='ChronicRecall',
            message_content=message
        )

        generated += 1

    return generated
def send_whatsapp_message(message_log):

    message_log.status = 'Delivered'

    message_log.provider_response = (
        'Test WhatsApp Success'
    )

    message_log.save()

    return True


def process_pending_messages():

    pending_logs = MessageLog.objects.filter(
        status='Pending'
    )

    count = 0

    for log in pending_logs:

        if log.channel == 'WhatsApp':

            send_whatsapp_message(log)

            count += 1

    return count

def run_reminders():

    followup_count = generate_followup_logs()

    chronic_count = generate_chronic_recall_logs()

    processed_count = process_pending_messages()

    return {
        'followups': followup_count,
        'chronic': chronic_count,
        'processed': processed_count,
    }