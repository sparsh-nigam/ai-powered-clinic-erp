from django.shortcuts import render
from appointments.models import Appointment
from consultations.models import ConsultationRecord


def prescription_print(
    request,
    appointment_id
):

    appointment = Appointment.objects.select_related(
        'patient',
        'doctor'
    ).get(
        id=appointment_id
    )

    consultation_record = ConsultationRecord.objects.filter(
        appointment=appointment
    ).first()

    treatment_items = []

    if consultation_record:
        treatment_items = consultation_record.treatment_items.all().order_by(
            'display_order',
            'id'
        )

    context = {
        'appointment': appointment,
        'consultation_record': consultation_record,
        'treatment_items': treatment_items,
    }

    return render(
        request,
        'prescription_print.html',
        context
    )