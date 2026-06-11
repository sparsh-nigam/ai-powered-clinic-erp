from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from doctors.models import Doctor
from appointments.models import Appointment
from operations.models import BillingSession, PatientFile
from consultations.models import ConsultationRecord, TreatmentItem
from doctors.models import TransferRequest
from datetime import datetime
from patients.models import Patient
from django.db.models import Q
from operations.models import PatientFile


@login_required
def doctor_dashboard(request):

    # Strict doctor-only access
    if request.user.role != 'DOCTOR':
        return HttpResponseForbidden(
            "Access restricted to verified doctor accounts."
        )

    # Authenticated doctor ownership bridge
    try:
        current_doctor = request.user.doctor_profile

    except Doctor.DoesNotExist:

        return render(request, 'doctor.html', {
            'doctor_profile_error': True
        })

    today = timezone.localdate()
    
    available_doctors = Doctor.objects.exclude(
            id=current_doctor.id
        )

    # Today's queue for logged-in doctor
    queue_appointments = Appointment.objects.filter(
        doctor=current_doctor,
        appointment_date=today
    ).exclude(
        status='Completed'
    ).select_related(
        'patient'
    ).order_by(
        'daily_token'
    )

    # Attach billing session status
    for appointment in queue_appointments:

        latest_session = BillingSession.objects.filter(
            appointment=appointment
        ).order_by('-id').first()

        appointment.billing_session_status = (
            latest_session.session_status
            if latest_session else 'Active'
        )

    # Active consultation workspace
    active_appointment_id = request.GET.get('appointment_id')

    active_appointment = None
    active_patient = None
    active_billing_session = None
    past_appointments = Appointment.objects.none()
    patient_documents = []
    consultation_record = None
    treatment_items = []
    
    
    if request.method == 'POST' and request.POST.get('action') == 'accept_transfer':

        transfer = TransferRequest.objects.get(
            id=request.POST.get('transfer_id'),
            to_doctor=current_doctor,
            status='Pending'
        )

        transfer.status = 'Accepted'
        transfer.save()

        appointment = transfer.appointment

        appointment.doctor = current_doctor
        appointment.status = 'Pending'
        appointment.save()

        return redirect(
            request.path + '?tab=transfer'
        )
        
    if request.method == 'POST' and request.POST.get('action') == 'reject_transfer':

        transfer = TransferRequest.objects.get(
            id=request.POST.get('transfer_id'),
            to_doctor=current_doctor,
            status='Pending'
        )

        transfer.status = 'Rejected'
        transfer.save()

        appointment = transfer.appointment

        appointment.status = 'Pending'
        appointment.save()

        return redirect(
            request.path + '?tab=transfer'
        )

    if active_appointment_id:

        active_appointment = Appointment.objects.filter(
            id=active_appointment_id,
            doctor=current_doctor
        ).select_related('patient').first()
        
        
        

        if active_appointment:

            active_patient = active_appointment.patient
            
            Appointment.objects.filter(
                doctor=current_doctor,
                status='In Consultation'
            ).exclude(
                id=active_appointment.id
            ).update(
                status='Pending'
            )

            if active_appointment.status == 'Pending':

                active_appointment.status = 'In Consultation'

                active_appointment.save(
                    update_fields=['status']
                )
            
            consultation_record, created = ConsultationRecord.objects.get_or_create(
                appointment=active_appointment
            )
            
            
            # Save Draft
            if request.method == 'POST' and consultation_record.status != 'Completed':

                
                delete_item_id = request.POST.get(
                    'delete_item_id'
                )

                if delete_item_id:

                    TreatmentItem.objects.filter(
                        id=delete_item_id,
                        consultation_record=consultation_record
                    ).delete()

                    return redirect(
                        f'{request.path}?appointment_id={active_appointment.id}&tab=workspace'
                    )
                    
                
                    
                    
                if request.POST.get('action') == 'transfer_patient':

                    target_doctor_id = request.POST.get(
                        'target_doctor'
                    )

                    if target_doctor_id:
                        
                        active_appointment.status = 'Transfer Requested'
                        active_appointment.save(
                            update_fields=['status']
                        )

                        TransferRequest.objects.create(
                            appointment=active_appointment,
                            from_doctor=current_doctor,
                            to_doctor=Doctor.objects.get(
                                id=target_doctor_id
                            ),
                            reason=request.POST.get(
                                'transfer_reason',
                                ''
                            ),
                            priority='Urgent'
                            if request.POST.get(
                                'transfer_priority'
                            ) == 'stat'
                            else 'Routine'
                        )

                        return redirect(
                            f'{request.path}?appointment_id={active_appointment.id}&tab=transfer'
                        )
                    
                consultation_record.chief_complaint = request.POST.get(
                    'chief_complaint',
                    ''
                )

                consultation_record.diagnosis = request.POST.get(
                    'diagnosis',
                    ''
                )

                consultation_record.clinical_notes = request.POST.get(
                    'clinical_notes',
                    ''
                )

                consultation_record.advice = request.POST.get(
                    'advice',
                    ''
                )
                
                consultation_record.followup_instruction = request.POST.get(
                    'followup_text',
                    ''
                )
                item_names = request.POST.getlist('item_name')

                if item_names:


                    item_types = request.POST.getlist('item_type')
                    item_dosages = request.POST.getlist('item_dosage')
                    item_durations = request.POST.getlist('item_duration')

                    for i in range(len(item_names)):

                        if not item_names[i].strip():
                            continue

                        TreatmentItem.objects.create(
                            consultation_record=consultation_record,
                            item_type=item_types[i],
                            name=item_names[i],
                            dosage=item_dosages[i],
                            duration=item_durations[i]
                        )
                    
                if request.POST.get('action') == 'complete_consultation':

                    consultation_record.status = 'Completed'

                    consultation_record.completed_at = timezone.now()

                    active_appointment.status = 'Completed'

                    active_appointment.save()

                
                    
                    
                consultation_record.save()

                return redirect(
                    f'{request.path}?appointment_id={active_appointment.id}&tab=workspace'
                )
            

            # Current billing session
            active_billing_session = BillingSession.objects.filter(
                appointment=active_appointment
            ).order_by('-id').first()

            # Patient timeline history
            past_appointments = Appointment.objects.filter(
                patient=active_patient
            ).exclude(
                id=active_appointment.id
            ).select_related('doctor').order_by(
                '-appointment_date'
            )
            
            for visit in past_appointments:

                consultation = ConsultationRecord.objects.filter(
                    appointment=visit
                ).first()

                visit.has_digital_prescription = False

                if consultation:

                    visit.has_digital_prescription = any([
                        consultation.chief_complaint,
                        consultation.diagnosis,
                        consultation.clinical_notes,
                        consultation.advice,
                        consultation.followup_instruction,
                        consultation.treatment_items.exists()
                    ])

                visit.has_physical_prescription = PatientFile.objects.filter(
                    appointment=visit,
                    file_type='Prescription'
                ).exists()
                
                physical_file = PatientFile.objects.filter(
                    appointment=visit,
                    file_type='Prescription'
                ).first()

                visit.physical_prescription_url = None

                if physical_file:
                    visit.physical_prescription_url = physical_file.file.url
            # Patient documents / reports
            patient_documents = PatientFile.objects.filter(
                appointment__patient=active_patient
            ).select_related(
                'appointment'
            ).order_by(
                '-uploaded_at'
            )

            

            if consultation_record:

                treatment_items = consultation_record.treatment_items.all().order_by(
                    'display_order',
                    'id'
                )
            
                 

    context = {
        'current_doctor': current_doctor,
        'queue_appointments': queue_appointments,
        'active_appointment': active_appointment,
        'active_patient': active_patient,
        'active_billing_session': active_billing_session,
        'past_appointments': past_appointments,
        'patient_documents': patient_documents,
        'consultation_record': consultation_record,
        'treatment_items': treatment_items,
        'available_doctors': available_doctors,
        'incoming_transfers': TransferRequest.objects.filter(
            to_doctor=current_doctor,
            status='Pending'
        ).select_related(
            'appointment',
            'from_doctor'
        ),

        'outgoing_transfers': TransferRequest.objects.filter(
            from_doctor=current_doctor
        ).select_related(
            'appointment',
            'to_doctor'
        ).order_by('-created_at')[:10],
    }

    return render(request, 'doctor.html', context)


@login_required
def schedules(request):

    doctors = Doctor.objects.all().order_by(
        'name'
    )

    today_date = timezone.localdate()

    selected_doctor = None

    # Doctor login -> auto load own schedule
    if request.user.role == 'DOCTOR':

        selected_doctor = Doctor.objects.filter(
            user=request.user
        ).first()

    # Staff / Super Owner -> use doctor selector
    else:

        doctor_id = request.GET.get(
            'doctor'
        )

        if doctor_id:

            selected_doctor = Doctor.objects.filter(
                id=doctor_id
            ).first()

    # Date filter
    selected_date = today_date

    date_param = request.GET.get(
        'date'
    )

    if date_param:

        try:

            selected_date = datetime.strptime(
                date_param,
                '%Y-%m-%d'
            ).date()

        except ValueError:

            selected_date = today_date

    # Selected Date Schedule
    today_appointments = Appointment.objects.none()

    # Future Schedule
    future_appointments = Appointment.objects.none()

    if selected_doctor:

        today_appointments = Appointment.objects.filter(
            doctor=selected_doctor,
            appointment_date=selected_date
        ).select_related(
            'patient',
            'consultation_record'
        ).order_by(
            'daily_token'
        )

        future_appointments = Appointment.objects.filter(
            doctor=selected_doctor,
            appointment_date__gt=today_date
        ).select_related(
            'patient'
        ).order_by(
            'appointment_date',
            'daily_token'
        )

    context = {

        'doctors': doctors,

        'selected_doctor': selected_doctor,

        'selected_date': selected_date.strftime(
            '%Y-%m-%d'
        ),

        'today_appointments': today_appointments,

        'future_appointments': future_appointments,

    }

    return render(
        request,
        'schedules.html',
        context
    )
    
@login_required
def my_patients(request):

    if request.user.role != 'DOCTOR':
        return HttpResponseForbidden(
            "Access restricted to verified doctor accounts."
        )

    current_doctor = request.user.doctor_profile
    
    search = request.GET.get('search', '')
    sort = request.GET.get('sort')

    appointments = Appointment.objects.filter(
        doctor=current_doctor
    ).select_related(
        'patient'
    ).order_by(
        '-appointment_date'
    )
    
    if search:

        appointments = appointments.filter(

            Q(patient__patient_id__icontains=search)

            |

            Q(patient__name__icontains=search)

            |

            Q(patient__phone__icontains=search)

        )

    patient_ids = []

    my_patients = []

    for appointment in appointments:

        if appointment.patient.id not in patient_ids:

            patient_ids.append(
                appointment.patient.id
            )

            latest_visit = Appointment.objects.filter(
                patient=appointment.patient
            ).order_by(
                '-appointment_date',
                '-id'
            ).first()

            appointment.patient.last_visit = (
                latest_visit.appointment_date
                if latest_visit
                else None
            )
            
            appointment.patient.total_visits = Appointment.objects.filter(
                patient=appointment.patient,
                doctor=current_doctor
            ).count()

            my_patients.append(
                appointment.patient
            )
            
    # Sorting
    if sort == 'name_asc':

        my_patients.sort(
            key=lambda patient: patient.name.lower()
        )

    elif sort == 'name_desc':

        my_patients.sort(
            key=lambda patient: patient.name.lower(),
            reverse=True
        )

    elif sort == 'id':

        my_patients.sort(
            key=lambda patient: patient.patient_id or ''
        )

    elif sort == 'oldest_visit':

        my_patients.sort(
            key=lambda patient: patient.last_visit
            or timezone.datetime.min.date()
        )

    # Default remains latest visit

    context = {

        'my_patients': my_patients,
        
        'search': search,

        'sort': sort,

    }

    return render(
        request,
        'my_patients.html',
        context
    )

@login_required
def my_patient_history(
    request,
    patient_id
):

    if request.user.role != 'DOCTOR':

        return HttpResponseForbidden(
            "Access restricted to verified doctor accounts."
        )

    current_doctor = request.user.doctor_profile

    patient = get_object_or_404(
        Patient,
        id=patient_id
    )

    doctor_has_access = Appointment.objects.filter(
        doctor=current_doctor,
        patient=patient
    ).exists()

    if not doctor_has_access:

        return HttpResponseForbidden(
            "You are not authorized to view this patient."
        )

    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related(
        'doctor'
    ).order_by(
        '-appointment_date',
        '-id'
    )

    for appt in appointments:

        appt.digital_prescription = ConsultationRecord.objects.filter(
            appointment=appt,
            status='Completed'
        ).first()

        appt.physical_prescription = PatientFile.objects.filter(
            appointment=appt,
            file_type='Prescription'
        ).order_by(
            '-id'
        ).first()
        
        appt.consultation_record = ConsultationRecord.objects.filter(
            appointment=appt
        ).first()

    digital_prescriptions = ConsultationRecord.objects.filter(
        appointment__patient=patient
    ).select_related(
        'appointment',
        'appointment__doctor'
    ).prefetch_related(
        'treatment_items'
    ).order_by(
        '-id'
    )

    patient_files = PatientFile.objects.filter(
        appointment__patient=patient
    ).order_by(
        '-id'
    )

    context = {

        'patient': patient,

        'appointments': appointments,

        'digital_prescriptions': digital_prescriptions,

        'prescriptions': patient_files.filter(
            file_type='Prescription'
        ),

        'reports': patient_files.filter(
            file_type='Report'
        ),

        'documents': patient_files.exclude(
            file_type__in=[
                'Prescription',
                'Patient Photo'
            ]
        ),

        'profile_photo': patient_files.filter(
            file_type='Patient Photo'
        ).first(),

    }

    return render(
        request,
        'my_patient_history.html',
        context
    )