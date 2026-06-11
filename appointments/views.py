from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from patients.models import Patient
from doctors.models import Doctor
from .models import Appointment
from operations.models import (
    BillingSession,
    BillingTransaction
)

def search_patient(request):
    search = request.GET.get('search')

    patients = Patient.objects.filter(
        Q(patient_id__iexact=search)
        |
        Q(phone__iexact=search)
    )

    if patients.exists():
        patient_list = []

        for patient in patients:
            patient_list.append({
                'id': patient.id,
                'patient_id': patient.patient_id,
                'name': patient.name,
                'age': patient.age,
                'phone': patient.phone,
                'gender': patient.gender,
                'disease': patient.disease,
                'is_active': patient.is_active_patient,
            })

        return JsonResponse({
            'success': True,
            'patients': patient_list
        })

    return JsonResponse({
        'success': False
    })

####################################

def appointments(request):
    doctors = Doctor.objects.all()
    today = timezone.localdate()
    
    Appointment.objects.filter(
        appointment_date__lt=today,
        status='Pending'
    ).update(
        status='Expired'
    )
    
    today_appointments = Appointment.objects.filter(
        appointment_date=today,
        daily_token__isnull=True
    ).order_by('created_at')

    for appointment in today_appointments:
        last_token = Appointment.objects.filter(
            appointment_date=today,
            daily_token__isnull=False
        ).order_by('-daily_token').first()

        if last_token:
            appointment.daily_token = (
                last_token.daily_token + 1
            )
        else:
            appointment.daily_token = 1

        appointment.save()

    appointments_data = Appointment.objects.filter(
        Q(appointment_date=today) | Q(updated_at__date=today)
    ).distinct().order_by('-updated_at','-id')

    if request.method == 'POST':
        patient_title = request.POST.get('patient_title')
        patient_name = request.POST.get('patient_name')
        patient_phone = request.POST.get('patient_phone')
        patient_gender = request.POST.get('patient_gender')
        patient_age = request.POST.get('patient_age')
        doctor_id = request.POST.get('doctor')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = timezone.localtime().time()
        status = request.POST.get('status')
        payment_status = request.POST.get('payment_status')
        payment_mode = request.POST.get('payment_mode')
        
        consultation_fee = request.POST.get('consultation_fee') or 0
        amount_received = request.POST.get('amount_received') or 0
        notes = request.POST.get('notes')

        existing_patient_id = request.POST.get('existing_patient_id')
        force_new_patient = request.POST.get('force_new_patient')
        
        ######## to attach only one phonenumber to eachh patient#
        
        # existing_patients = Patient.objects.filter(phone=patient_phone)

        # if existing_patients.exists() and not existing_patient_id and not force_new_patient:
        #     context = {
        #         'doctors': doctors,
        #         'today': today,
        #         'appointments_data': appointments_data,
        #         'existing_patients': existing_patients
        #     }
        #     return render(
        #         request,
        #         'appointments/appointments.html',
        #         context
        #     )

        if existing_patient_id:
            patient = Patient.objects.get(id=existing_patient_id)
        else:
            patient = Patient.objects.create(
                title=patient_title,
                name=patient_name,
                age=patient_age,
                gender=patient_gender,
                phone=patient_phone,
                disease=request.POST.get('disease'),
                appointment_date=appointment_date
            )

        doctor = Doctor.objects.get(id=doctor_id)
        daily_token = None

        if appointment_date == str(today):
            last_token = Appointment.objects.filter(
                appointment_date=today,
                daily_token__isnull=False
            ).order_by('-daily_token').first()

            if last_token:
                daily_token = last_token.daily_token + 1
            else:
                daily_token = 1

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            daily_token=daily_token,
            status=status,
            payment_status=payment_status,
            payment_mode=payment_mode,
            amount_received=amount_received,
            notes=notes,
            created_by=request.user
        )
        
        billing_session = BillingSession.objects.create(
            session_number=f"BILL-{appointment.id}",
            patient=patient,
            appointment=appointment,
            visit_type='OPD',
            session_status='Active'
        )

        consultation_amount = float(consultation_fee or 0)
        received_amount = float(amount_received or 0)
        pending_amount = consultation_amount - received_amount

        if pending_amount < 0:
            pending_amount = 0

        # FIXED: Captured request.FILES.get('file') directly to attach your proof object
        uploaded_proof_file = request.FILES.get('file')

        BillingTransaction.objects.create(
            patient=patient,
            appointment=appointment,
            billing_session=billing_session,
            transaction_type='Consultation',
            total_amount=consultation_amount,
            paid_amount=received_amount,
            pending_amount=pending_amount,
            payment_status=payment_status,
            payment_mode=payment_mode,
            payment_proof=uploaded_proof_file,  # Tied safely to your storage model field
            notes='Consultation Advance Payment'
        )
        
        # DOCUMENT VAULT FIX: Seamlessly sync and register the file to longitudinal history vault
        if uploaded_proof_file:
            from operations.models import PatientFile
            PatientFile.objects.create(
                appointment=appointment,
                file_type='Document',
                custom_name='Appointment Payment Proof',
                file=uploaded_proof_file
            )
        
        payment_status = request.POST.get('payment_status')
        if payment_status in ['Paid', 'Waived']:
            patient.last_paid_consultation = appointment_date
            patient.save()

        return redirect(
            'appointment_success',
            id=appointment.id
        )

    context = {
        'doctors': doctors,
        'today': today,
        'appointments_data': appointments_data
    }

    return render(
        request,
        'appointments/appointments.html',
        context
    )

##############################


def appointment_success(request, id):

    appointment = Appointment.objects.get(id=id)

        
    linked_transaction = BillingTransaction.objects.filter(
        appointment=appointment,
        transaction_type='Consultation'
    ).order_by('-id').first()

    if linked_transaction:
        consultation_fee_status = linked_transaction.payment_status
    else:
        consultation_fee_status = appointment.payment_status

    context = {
        'appointment': appointment,
        'consultation_fee_status': consultation_fee_status,
    }

    return render(
        request,
        'appointments/appointment_success.html',
        context
    )