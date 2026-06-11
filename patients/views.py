from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from appointments.models import Appointment
from operations.models import BillingSession, BillingTransaction  # IMPORTED: Needed to track complete billing session states
from operations.models import PatientFile
from .models import Patient
from django.contrib import messages
from consultations.models import ConsultationRecord
from operations.models import AppointmentFollowUp,   FollowUpCondition
from operations.models import PatientCondition

def patient_history(request, pk):
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':

        uploaded_file = request.FILES.get('file')
        file_type = request.POST.get('file_type')

        if uploaded_file and file_type:

            latest_appointment = Appointment.objects.filter(
                patient=patient
            ).order_by('-id').first()

            PatientFile.objects.create(
                appointment=latest_appointment,
                file_type=file_type,
                file=uploaded_file
            )

            messages.success(
                request,
                'Document uploaded successfully.'
            )

            return redirect(
                'patient_history',
                pk=patient.pk
            )
    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related(
        'doctor',
        'followup'
    ).order_by('-id')
    
    latest_appointment = appointments.first()
    
    for appt in appointments:

        appt.digital_prescription = ConsultationRecord.objects.filter(
            appointment=appt,
            status='Completed'
        ).first()

        appt.physical_prescription = PatientFile.objects.filter(
            appointment=appt,
            file_type='Prescription'
        ).order_by('-id').first()
        
        appt.followup_editable = False

        if latest_appointment:

            appointment_age = (
                timezone.localdate() -
                appt.appointment_date
            ).days

            if (
                appt.id == latest_appointment.id
                and appointment_age <= 6
            ):
                appt.followup_editable = True
                
        if hasattr(appt, 'followup'):

            appt.selected_conditions = list(
                appt.followup.conditions.values_list(
                    'condition_name',
                    flat=True
                )
            )

        else:

            appt.selected_conditions = []
        
    digital_prescriptions = ConsultationRecord.objects.filter(
        appointment__patient=patient
    ).select_related(
        'appointment',
        'appointment__doctor'
    ).prefetch_related(
        'treatment_items'
    ).order_by('-id')
    billing_sessions = BillingSession.objects.filter(patient=patient).order_by('-id')
    patient_files = PatientFile.objects.filter(
        appointment__patient=patient
    ).order_by('-id')
    payment_proofs = BillingTransaction.objects.filter(
        patient=patient,
        payment_proof__isnull=False
    ).exclude(
        payment_proof=''
    ).order_by('-id')
    
    appointment_payment_proofs = Appointment.objects.filter(
        patient=patient,
        payment_proof__isnull=False
    ).exclude(
        payment_proof=''
    ).order_by('-id')
    
    condition_records = PatientCondition.objects.filter(
        patient=patient
    ).order_by('condition')
    context = {
        'condition_records': condition_records,
        'common_conditions': PatientCondition.COMMON_CONDITIONS,
        'patient': patient,
        'appointments': appointments,
        'billing_sessions': billing_sessions,
        'digital_prescriptions': digital_prescriptions,
        'prescriptions': patient_files.filter(file_type='Prescription'),
        'documents': patient_files.exclude(file_type__in=['Prescription', 'Patient Photo']),
        'reports': patient_files.filter(file_type='Report'),
        'payment_proofs': payment_proofs,
        'appointment_payment_proofs': appointment_payment_proofs,
        'patient_photos': patient_files.filter(file_type='Patient Photo'),
        'profile_photo': patient_files.filter(file_type='Patient Photo').first(),
    }
    
    return render(request, 'patients/patient_history.html', context)

def patients(request):
    from appointments.models import Appointment

    today = timezone.localdate()
    patients_data = Patient.objects.all().order_by('-id')

    search = request.GET.get('search')
    gender = request.GET.get('gender')
    status = request.GET.get('status')

    # Apply search filters
    if search:
        patients_data = patients_data.filter(
            Q(patient_id__icontains=search)
            |
            Q(name__icontains=search)
            |
            Q(phone__icontains=search)
        )

    if gender:
        patients_data = patients_data.filter(
            gender=gender
        )

    total_patients = Patient.objects.count()
    
    today_patients = Appointment.objects.filter(
        created_at__date=today
    ).values(
        'patient'
    ).distinct().count()

    active_patients = 0
    expired_patients = 0

    pending_count = 0
    completed_count = 0
    cancelled_count = 0
    expired_count = 0
    no_appointment_count = 0

    # Loop through patients to dynamically bind metrics and live session tracking keys
    for patient in patients_data:
        
        patient.registered_today = Appointment.objects.filter(
            patient=patient,
            created_at__date=today
        ).exists()

        latest_appointment = Appointment.objects.filter(
            patient=patient
        ).order_by('-id').first()

        # FIX: Fetch the absolute latest full billing session record for this specific patient
        has_due_session = BillingSession.objects.filter(
            patient=patient,
            session_status='Due Pending'
        ).exists()

        if has_due_session:
            patient.latest_session_status = 'Due Pending'

        else:
            latest_session = BillingSession.objects.filter(
                patient=patient
            ).order_by('-id').first()

            if latest_session:
                patient.latest_session_status = latest_session.session_status
            else:
                patient.latest_session_status = 'No Session'

        if latest_appointment:
            patient.latest_appointment_status = (
                latest_appointment.status
            )
            patient.latest_payment_status = (
                latest_appointment.payment_status
            )
        else:
            patient.latest_appointment_status = (
                'No Appointment'
            )
            patient.latest_payment_status = '-'

        if patient.is_active_patient:
            active_patients += 1
        else:
            expired_patients += 1

        # Incremental math loops for your sidebar sliding analytics engine counters
        if patient.latest_appointment_status == 'Pending':
            pending_count += 1
        elif patient.latest_appointment_status == 'Completed':
            completed_count += 1
        elif patient.latest_appointment_status == 'Cancelled':
            cancelled_count += 1
        elif patient.latest_appointment_status == 'Expired':
            expired_count += 1
        elif patient.latest_appointment_status == 'No Appointment':
            no_appointment_count += 1

    # Custom post-loop list filtering for your top dashboard card clicks
    if status == 'Active':
        patients_data = [
            patient for patient in patients_data
            if patient.is_active_patient
        ]

    elif status == 'Inactive':
        patients_data = [
            patient for patient in patients_data
            if not patient.is_active_patient
        ]

    context = {
        'patients_data': patients_data,
        'total_patients': total_patients,
        'today_patients': today_patients,
        'active_patients': active_patients,
        'inactive_patients': expired_patients,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'expired_count': expired_count,
        'no_appointment_count': no_appointment_count,
    }

    return render(
        request,
        'patients/patients.html',
        context
    )
    
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    existing_conditions = list(
        patient.condition_records.values_list(
            'condition',
            flat=True
        )
    )

    custom_condition = patient.condition_records.filter(
        is_custom=True
    ).first()
    if request.method == 'POST':
        

        # Retrieve form data
        patient.name = request.POST.get('name')
        patient.phone = request.POST.get('phone')
        patient.age = request.POST.get('age')
        patient.disease = request.POST.get('disease')
        patient.blood_group = request.POST.get('blood_group')
        patient.allergies = request.POST.get('allergies')
        patient.chronic_conditions =''
        patient.address = request.POST.get('address')
        patient.height = request.POST.get('height') or None
        patient.weight = request.POST.get('weight') or None
        
        # Save to database
        patient.save()
        PatientCondition.objects.filter(
            patient=patient
        ).delete()

        selected_conditions = request.POST.getlist(
            'conditions'
        )

        for condition in selected_conditions:

            PatientCondition.objects.create(
                patient=patient,
                condition=condition
            )

        custom_condition = request.POST.get(
            'custom_condition'
        )

        if custom_condition:

            PatientCondition.objects.create(
                patient=patient,
                condition=custom_condition.strip(),
                is_custom=True
            )
        messages.success(request, 'Patient profile updated successfully.')
        
        # Redirect back to the history page
        return redirect('patient_history', pk=patient.pk)

    context = {
        'patient': patient,
        'blood_groups': [bg[0] for bg in Patient.BloodGroup_Choices],
        'existing_conditions': existing_conditions,
        'custom_condition': (
            custom_condition.condition
            if custom_condition else ''
        )
    }
    return render(request, 'patients/edit_patient.html', context)

def add_patient(request):

    if request.method == 'POST':

        patient = Patient.objects.create(
            title=request.POST.get('title'),
            name=request.POST.get('name'),
            age=request.POST.get('age'),
            gender=request.POST.get('gender'),
            phone=request.POST.get('phone'),

            address=request.POST.get('address'),
            disease=request.POST.get('disease'),
            blood_group=request.POST.get('blood_group'),

            allergies=request.POST.get('allergies'),
            chronic_conditions='',

            height=request.POST.get('height') or None,
            weight=request.POST.get('weight') or None,
        )
        
        selected_conditions = request.POST.getlist(
            'conditions'
        )

        for condition in selected_conditions:

            PatientCondition.objects.create(
                patient=patient,
                condition=condition
            )

        custom_condition = request.POST.get(
            'custom_condition'
        )

        if custom_condition:

            PatientCondition.objects.create(
                patient=patient,
                condition=custom_condition.strip(),
                is_custom=True
            )

        messages.success(
            request,
            'Patient registered successfully.'
        )

        return redirect('patients')

    context = {
        'title_choices': Patient.Title_Choices,
        'gender_choices': Patient.Gender_Choices,
        'blood_groups': Patient.BloodGroup_Choices,
    }

    return render(
        request,
        'patients/add_patient.html',
        context
    )
    
def save_followup(request, appointment_id):

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id
    )

    latest_appointment = Appointment.objects.filter(
        patient=appointment.patient
    ).order_by('-id').first()

    if appointment.id != latest_appointment.id:

        messages.error(
            request,
            'Follow-up can only be added to latest appointment.'
        )

        return redirect(
            'patient_history',
            pk=appointment.patient.id
        )

    appointment_age = (
        timezone.localdate() -
        appointment.appointment_date
    ).days

    if appointment_age > 6:

        messages.error(
            request,
            'Follow-up editing window expired.'
        )

        return redirect(
            'patient_history',
            pk=appointment.patient.id
        )

    selected_conditions = request.POST.getlist(
        'conditions'
    )

    custom_condition = request.POST.get(
        'custom_condition'
    )

    if custom_condition:
        selected_conditions.append(
            custom_condition.strip()
        )

    followup_topic = request.POST.get(
        'followup_topic'
    )
    
    followup_days = int(
        request.POST.get('followup_days')
    )

    days_passed = (
        timezone.localdate() -
        appointment.appointment_date
    ).days

    if followup_days <= days_passed:

        messages.error(
            request,
            'Follow-up period already passed.'
        )

        return redirect(
            'patient_history',
            pk=appointment.patient.id
        )

    followup_due_date = (
        appointment.appointment_date +
        timezone.timedelta(days=followup_days)
    )

    followup, created = AppointmentFollowUp.objects.update_or_create(
        appointment=appointment,
        defaults={
            'patient': appointment.patient,
            'category': (
                selected_conditions[0]
                if selected_conditions
                else 'General'
            ),
            'followup_topic': followup_topic,
            'followup_days': followup_days,
            'followup_due_date': followup_due_date,
            'created_by': request.user,
            'reminder_enabled': True,
        }
    )

    FollowUpCondition.objects.filter(
        followup=followup
    ).delete()

    for condition in selected_conditions:

        FollowUpCondition.objects.create(
            followup=followup,
            condition_name=condition,
            is_custom=condition not in [
                'Diabetes',
                'Hypertension',
                'Kidney Disease',
                'Liver Disease',
                'Thyroid',
                'Asthma',
                'Heart Disease',
            ]
        )

    messages.success(
        request,
        'Follow-up saved successfully.'
    )

    return redirect(
        'patient_history',
        pk=appointment.patient.id
    )
    
def add_patient_condition(request, patient_id):

    patient = get_object_or_404(
        Patient,
        id=patient_id
    )

    category = request.POST.get('category')
    custom_condition = request.POST.get('custom_condition')

    if category == 'Other':
        condition_name = custom_condition.strip()
        is_custom = True
    else:
        condition_name = category
        is_custom = False

    if not condition_name:
        messages.error(
            request,
            'Condition name is required.'
        )
        return redirect(
            'patient_history',
            pk=patient.id
        )

    exists = PatientCondition.objects.filter(
        patient=patient,
        condition__iexact=condition_name
    ).exists()

    if exists:
        messages.warning(
            request,
            'Condition already exists.'
        )
        return redirect(
            'patient_history',
            pk=patient.id
        )

    PatientCondition.objects.create(
        patient=patient,
        condition=condition_name,
        is_custom=is_custom
    )

    messages.success(
        request,
        'Condition added successfully.'
    )

    return redirect(
        'patient_history',
        pk=patient.id
    )
    
def delete_patient_condition(request, condition_id):

    condition = get_object_or_404(
        PatientCondition,
        id=condition_id
    )

    patient_id = condition.patient.id

    condition.delete()

    messages.success(
        request,
        'Condition removed successfully.'
    )

    return redirect(
        'patient_history',
        pk=patient_id
    )