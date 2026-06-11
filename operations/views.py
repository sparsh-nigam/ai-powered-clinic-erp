from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import Patient
from .models import PatientFile, BillingTransaction, BillingSession, BillingItem
from .models import AppointmentFollowUp, FollowUpCondition, MessageLog


def queue_management(request):
    today = timezone.localdate()
    
    appointments = Appointment.objects.filter(
        appointment_date=today
    ).select_related('patient', 'doctor').order_by('daily_token')
    
    for appointment in appointments:
        latest_session = BillingSession.objects.filter(
            appointment=appointment
        ).order_by('-id').first()
        appointment.billing_session_status = latest_session.session_status if latest_session else 'Active'

    context = {
        'appointments': appointments,
        'waiting_count': appointments.filter(status='Pending').count(),
        'in_consultation_count': appointments.filter( status='In Consultation' ).count(),
        'completed_count': appointments.filter(status='Completed').count(),
        'cancelled_count': appointments.filter(status='Cancelled').count(),
        'expired_count': appointments.filter(status='Expired').count(),
        'paid_count': appointments.filter(payment_status='Paid').count(),
        'pending_payment_count': appointments.filter(payment_status='Pending').count(),
        'waived_count': appointments.filter(payment_status='Waived').count(),
        'live_consultations': appointments.filter(status='In Consultation'),
        'doctor_queue': [
            {
                'doctor': doc,
                'pending_count': appointments.filter(
                    doctor=doc,
                    status='Pending'
                ).count(),

                'in_consultation_count': appointments.filter(
                    doctor=doc,
                    status='In Consultation'
                ).count()
            } for doc in Doctor.objects.all()
        ],
    }
    context['remaining_count'] = ( context['waiting_count'] + context['in_consultation_count'] )
    return render(request, 'operations/queue_management.html', context)


def action_center(request, id):
    appointment = get_object_or_404(Appointment.objects.select_related('patient', 'doctor'), id=id)
    
    latest_session = BillingSession.objects.filter(appointment=appointment).order_by('-id').first()
    appointment.billing_session_status = latest_session.session_status if latest_session else 'Active'
    
    if request.method == 'POST':
        if request.POST.get('form_type') == 'followup':

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

            followup_days = request.POST.get(
                'followup_days'
            )

            try:
                followup_days = int(followup_days)
            except (TypeError, ValueError):
                messages.error(
                    request,
                    'Follow-up days must be a valid number.'
                )
                return redirect(
                    'action_center',
                    id=appointment.id
                )

            appointment_age = (
                timezone.localdate() -
                appointment.appointment_date
            ).days

            if appointment_age > 6:

                messages.error(
                    request,
                    'Follow-up can only be added within 6 days of appointment.'
                )

                return redirect(
                    'action_center',
                    id=appointment.id
                )
            days_passed = (
                timezone.localdate() -
                appointment.appointment_date
            ).days

            if followup_days <= days_passed:

                messages.error(
                    request,
                    (
                        f'Follow-up period already passed. '
                        f'Appointment is {days_passed} day(s) old.'
                    )
                )

                return redirect(
                    'action_center',
                    id=appointment.id
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
                'action_center',
                id=appointment.id
            )
            
        status_action = request.POST.get('status_action')
        if status_action in ['pending', 'complete', 'cancel']:
            status_map = {'pending': 'Pending', 'complete': 'Completed', 'cancel': 'Cancelled'}
            appointment.status = status_map[status_action]
            appointment.save()
            return redirect('queue_management')
            
        uploaded_file = request.FILES.get('file')
        file_type = request.POST.get('file_type')
        if uploaded_file and file_type:
            PatientFile.objects.create(
                appointment=appointment,
                file_type=file_type,
                file=uploaded_file
            )
            return redirect('action_center', id=appointment.id)
        
    followup = AppointmentFollowUp.objects.filter(
        appointment=appointment
    ).first()
    
    selected_conditions = []

    if followup:

        selected_conditions = list(
            followup.conditions.values_list(
                'condition_name',
                flat=True
            )
        )

    files = PatientFile.objects.filter(appointment=appointment)
    context = {
        'followup': followup,
        'appointment': appointment,
        'selected_conditions': selected_conditions,
        'prescriptions': files.filter(file_type='Prescription'),
        'reports': files.filter(file_type='Report'),
        'documents': files.filter(file_type='Document'),
        'patient_photos': files.filter(file_type='Patient Photo'),
    }
    return render(request, 'operations/action_center.html', context)


def billing(request, id=0):
    appointment = None
    patient = None
    billing_session = None

    if id != 0:
        appointment = get_object_or_404(Appointment.objects.select_related('patient', 'doctor'), id=id)
        patient = appointment.patient
        billing_session, created = BillingSession.objects.get_or_create(
            appointment=appointment,
            defaults={
                'session_number': f"BILL-{appointment.id}",
                'patient': patient,
                'visit_type': 'OPD',
            }
        )
        if billing_session.session_status == 'Completed':
            return redirect('final_invoice', session_id=billing_session.id)

    patient_id = request.GET.get('patient_id')
    patient_search = request.GET.get('patient_search')
    new_session = request.GET.get('new_session')
    session_id = request.GET.get('session')

    if not appointment and (patient_id or patient_search):
        try:
            if patient_id:
                patient = Patient.objects.get(id=patient_id)
            elif patient_search:
                patient = Patient.objects.get(patient_id=patient_search)
        except Patient.DoesNotExist:
            messages.error(request, f"No profile record found matching key reference target.")
            return render(request, 'operations/billing.html', {'overall_billing_status': 'Pending'})

        if new_session == 'true':
            total_sessions = BillingSession.objects.filter(patient=patient).count()
            billing_session = BillingSession.objects.create(
                session_number=f"BILL-{patient.patient_id}-{total_sessions + 1}",
                patient=patient,
                visit_type='Manual',
                session_status='Active'
            )
            return redirect(f'/operations/billing/0/?patient_search={patient.patient_id}&session={billing_session.id}')

    if session_id and patient:
        billing_session = get_object_or_404(
            BillingSession.objects.filter(patient=patient),
            id=session_id
        )

        # Restore appointment context for reopened appointment sessions
        if billing_session.appointment and not appointment:
            appointment = billing_session.appointment

        if billing_session.session_status == 'Completed':
            return redirect(f'/operations/final-invoice/{billing_session.id}/')

    if request.method == 'POST' and patient:
        close_session = request.POST.get('close_session')
        if close_session and billing_session:
            billing_session.session_status = 'Completed'
            billing_session.save()
            return JsonResponse({'success': True})

        with transaction.atomic():
            if billing_session and billing_session.session_status == 'Completed':
                return JsonResponse({'success': False, 'message': 'Session is securely locked and archived.'})

            form_type = request.POST.get('form_type')

            if form_type == 'clear_due':
                try:
                    remaining_payment = Decimal(request.POST.get('repayment_amount', '0') or '0')
                except InvalidOperation:
                    return JsonResponse({'success': False, 'message': 'Invalid numerical text format submitted.'})

                pending_transactions = BillingTransaction.objects.filter(
                    billing_session=billing_session, pending_amount__gt=0
                ).order_by('created_at')

                actual_cleared_amount = Decimal('0')
                
                for due_transaction in pending_transactions:
                    if remaining_payment <= 0:
                        break
                    due_amount = due_transaction.pending_amount
                    if remaining_payment >= due_amount:
                        due_transaction.paid_amount += due_amount
                        due_transaction.pending_amount = 0
                        due_transaction.payment_status = 'Paid'
                        
                        actual_cleared_amount += due_amount
                        
                        remaining_payment -= due_amount
                    else:
                        due_transaction.paid_amount += remaining_payment
                        due_transaction.pending_amount -= remaining_payment
                        
                        actual_cleared_amount += remaining_payment
                        
                        due_transaction.payment_status = 'Dues Pending'
                        remaining_payment = 0
                    due_transaction.save()

                totals = BillingTransaction.objects.filter(billing_session=billing_session, is_void=False).aggregate(
                    b=Sum('total_amount'), p=Sum('paid_amount'), d=Sum('pending_amount')
                )
                billing_session.total_amount = totals['b'] or 0
                billing_session.total_paid = totals['p'] or 0
                billing_session.total_due = totals['d'] or 0
                billing_session.session_status = 'Completed' if billing_session.total_due <= 0 else 'Due Pending'
                 
                payment_proof = request.FILES.get('payment_proof')

                BillingTransaction.objects.create(
                    billing_session=billing_session,
                    patient=patient,
                    appointment=appointment,
                    transaction_type='Due Clearance',
                    total_amount=0,
                    paid_amount=actual_cleared_amount,   
                    pending_amount=0,
                    payment_status='Paid',
                    payment_mode=request.POST.get('payment_mode'),
                    transaction_id=request.POST.get('transaction_id'),
                    payment_proof=payment_proof,
                    payment_received_at=timezone.now(),
                    notes='Due cleared from patient history settlement.'
                )
                
                
                if billing_session.session_status == 'Completed':
                    if appointment:
                        appointment.payment_status = 'Paid'
                        appointment.pending_amount = 0
                        appointment.save()
                        # Preserves original timing trace window by tracking from original encounter date
                        patient.last_paid_consultation = appointment.appointment_date
                        patient.save()

                billing_session.save()

                return JsonResponse({
                    'success': True,
                    'total_bill': float(billing_session.total_amount),
                    'total_paid': float(billing_session.total_paid),
                    'total_pending': float(billing_session.total_due),
                    'session_status': billing_session.session_status,
                    'session_id': billing_session.id
                })

            finalize_session = request.POST.get('finalize_session')
            if finalize_session == 'true' and billing_session:

                settlement_amount = Decimal(
                    request.POST.get('paid_amount', '0') or '0'
                )

                transactions = BillingTransaction.objects.filter(
                    billing_session=billing_session,
                    is_void=False
                ).order_by('created_at')

                remaining_settlement = settlement_amount

                for trx in transactions:

                    if remaining_settlement <= 0:
                        break

                    if trx.pending_amount <= 0:
                        continue

                    due = trx.pending_amount

                    if remaining_settlement >= due:

                        trx.paid_amount += due
                        trx.pending_amount = 0
                        trx.payment_status = 'Paid'

                        remaining_settlement -= due

                    else:

                        trx.paid_amount += remaining_settlement
                        trx.pending_amount -= remaining_settlement
                        trx.payment_status = 'Dues Pending'

                        remaining_settlement = Decimal('0')

                    trx.payment_mode = request.POST.get('payment_mode')
                    trx.transaction_id = request.POST.get('transaction_id')

                    if request.FILES.get('payment_proof'):
                        trx.payment_proof = request.FILES.get('payment_proof')

                    trx.payment_received_at = timezone.now()

                    trx.save()

                totals = BillingTransaction.objects.filter(
                    billing_session=billing_session,
                    is_void=False
                ).aggregate(
                    b=Sum('total_amount'),
                    p=Sum('paid_amount'),
                    d=Sum('pending_amount')
                )

                billing_session.total_amount = totals['b'] or 0
                billing_session.total_paid = totals['p'] or 0
                billing_session.total_due = totals['d'] or 0

                billing_session.session_status = (
                    'Completed'
                    if billing_session.total_due <= 0
                    else 'Due Pending'
                )

                billing_session.save()

                return JsonResponse({
                    'success': True,
                    'session_status': billing_session.session_status,
                    'session_id': billing_session.id
                })

            try:
                total_amount = Decimal(request.POST.get('total_amount', '0') or '0')
                paid_amount = Decimal(request.POST.get('paid_amount', '0') or '0')
            except InvalidOperation:
                return JsonResponse({'success': False, 'message': 'Mathematical parsing alignment syntax fault.'})

            payment_mode = request.POST.get('payment_mode')
            transaction_id = request.POST.get('transaction_id')
            
            item_maps = {'medicine': 'medicine_name[]', 'procedure': 'procedure_name[]', 'emergency': 'emergency_name[]'}
            item_names = request.POST.getlist(item_maps.get(form_type, '')) if form_type in item_maps else []

            pending_amount = max(Decimal('0'), total_amount - paid_amount)
            if pending_amount <= 0:
                payment_status = 'Paid'
            elif paid_amount <= 0:
                payment_status = 'Pending'
            else:
                payment_status = 'Dues Pending'
                
            if form_type in ['medicine', 'procedure', 'emergency']:

                paid_amount = Decimal('0')
                pending_amount = total_amount
                payment_status = 'Pending'

            t_type = form_type.capitalize() if form_type else 'Unknown'
            billing_transaction, _ = BillingTransaction.objects.update_or_create(
                billing_session=billing_session, transaction_type=t_type, is_void=False,
                defaults={
                    'patient': patient, 'appointment': appointment, 'total_amount': total_amount,
                    'paid_amount': paid_amount, 'pending_amount': pending_amount, 'payment_status': payment_status,
                    'payment_mode': payment_mode, 'transaction_id': transaction_id, 'notes': ', '.join(item_names)
                }
            )
            if paid_amount > 0:
                billing_transaction.payment_received_at = timezone.now()
                billing_transaction.save(
                    update_fields=['payment_received_at']
                )

            if request.FILES.get('payment_proof'):
                billing_transaction.payment_proof = request.FILES.get('payment_proof')
                billing_transaction.save()

            if form_type in ['medicine', 'procedure', 'emergency']:
                billing_transaction.items.all().delete()
                qtys = request.POST.getlist(f'{form_type}_qty[]')
                prices = request.POST.getlist(f'{form_type}_price[]')
                
                for idx, name in enumerate(item_names):
                    if name.strip():
                        try:
                            q = int(qtys[idx]) if idx < len(qtys) else 1
                            p = Decimal(prices[idx]) if idx < len(prices) else Decimal('0')
                        except (ValueError, InvalidOperation):
                            q, p = 1, Decimal('0')
                        
                        if form_type != 'medicine' or p > 0:
                            BillingItem.objects.create(
                                billing_transaction=billing_transaction, item_name=name,
                                quantity=q, price=p, total_price=q * p
                            )

            if appointment and form_type == 'consultation':
                appointment.total_amount, appointment.paid_amount = total_amount, paid_amount
                appointment.pending_amount, appointment.payment_status = pending_amount, payment_status
                if payment_status == 'Paid':
                    patient.last_paid_consultation = timezone.localdate()
                    patient.save()
                appointment.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                transactions_query = BillingTransaction.objects.filter(billing_session=billing_session, is_void=False)
                return JsonResponse({
                    'success': True,
                    'total_bill': float(transactions_query.aggregate(s=Sum('total_amount'))['s'] or 0),
                    'total_paid': float(transactions_query.aggregate(s=Sum('paid_amount'))['s'] or 0),
                    'total_pending': float(transactions_query.aggregate(s=Sum('pending_amount'))['s'] or 0),
                    'session_status': billing_session.session_status,
                    'session_id': billing_session.id
                })

    transactions = BillingTransaction.objects.filter(billing_session=billing_session, is_void=False).order_by('-created_at') if billing_session else BillingTransaction.objects.none()
    
    sums = transactions.aggregate(b=Sum('total_amount'), p=Sum('paid_amount'), d=Sum('pending_amount'))
    total_bill, total_paid, total_pending = sums['b'] or 0, sums['p'] or 0, sums['d'] or 0

    if total_bill == 0:
        overall_billing_status = 'No Active Session'
    elif total_pending <= 0 and total_bill > 0:
        overall_billing_status = 'Paid'
    elif total_paid <= 0:
        overall_billing_status = 'Pending'
    else:
        overall_billing_status = 'Dues Pending'

    med_t = transactions.filter(transaction_type='Medicine').first()
    proc_t = transactions.filter(transaction_type='Procedure').first()
    emerg_t = transactions.filter(transaction_type='Emergency').first()

    context = {
        'appointment': appointment, 'patient': patient, 'billing_session': billing_session,
        'transactions': transactions, 'total_bill': total_bill, 'total_paid': total_paid, 'total_pending': total_pending,
        'overall_billing_status': overall_billing_status, 'billing_sessions': BillingSession.objects.filter(patient=patient).order_by('-created_at') if patient else [],
        'consultation_transaction': transactions.filter(transaction_type='Consultation').first(),
        'medicine_items_data': med_t.items.all() if med_t else [],
        'procedure_items_data': proc_t.items.all() if proc_t else [],
        'emergency_items_data': emerg_t.items.all() if emerg_t else [],
        'edit_locked': billing_session.session_status in ['Completed', 'Due Pending'] if billing_session else False,
        'allow_due_clearance': billing_session.session_status == 'Due Pending' if billing_session else False,
    }
    return render(request, 'operations/billing.html', context)


def delete_billing_transaction(request, id):
    billing_transaction = get_object_or_404(BillingTransaction, id=id)
    billing_transaction.is_void = True
    billing_transaction.save()
    return JsonResponse({'success': True})


def billing_history(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    billing_sessions = BillingSession.objects.filter(patient=patient).order_by('-created_at')
    
    context = {
        'patient': patient,
        'billing_sessions': billing_sessions,
        'total_sessions': billing_sessions.count(),
        'total_revenue': billing_sessions.aggregate(s=Sum('total_paid'))['s'] or 0,
        'total_due': billing_sessions.aggregate(s=Sum('total_due'))['s'] or 0,
        'completed_sessions': billing_sessions.filter(session_status='Completed').count(),
    }
    return render(request, 'operations/billing-history.html', context)


def final_invoice(request, session_id):
    billing_session = get_object_or_404(BillingSession.objects.select_related('patient'), id=session_id)
    transactions = BillingTransaction.objects.filter(billing_session=billing_session, is_void=False)
    
    sums = {
        'b': billing_session.total_amount,
        'p': billing_session.total_paid,
        'd': billing_session.total_due,
    }
    context = {
        'billing_session': billing_session,
        'patient': billing_session.patient,
        'transactions': transactions,
        'total_bill': sums['b'] or 0,
        'total_paid': sums['p'] or 0,
        'total_pending': sums['d'] or 0,
    }
    return render(request, 'operations/final_invoice.html', context)


def download_invoice_pdf(request, session_id):
    billing_session = get_object_or_404(BillingSession.objects.select_related('patient'), id=session_id)
    transactions = BillingTransaction.objects.filter(billing_session=billing_session, is_void=False)
    
    sums = {
        'b': billing_session.total_amount,
        'p': billing_session.total_paid,
        'd': billing_session.total_due,
    }
    context = {
        'billing_session': billing_session,
        'patient': billing_session.patient,
        'transactions': transactions,
        'total_bill': sums['b'] or 0,
        'total_paid': sums['p'] or 0,
        'total_pending': sums['d'] or 0,
    }
    
    html = get_template('operations/final_invoice.html').render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice-{billing_session.session_number}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response if not pisa_status.err else HttpResponse('PDF generation failed', status=500)


@login_required
def communication_center(request):

    today = timezone.localdate()

    due_today = AppointmentFollowUp.objects.filter(
        followup_due_date=today,
        reminder_enabled=True
    ).select_related('patient')

    upcoming_followups = AppointmentFollowUp.objects.filter(
        followup_due_date__gt=today,
        reminder_enabled=True
    ).order_by(
        'followup_due_date'
    ).select_related('patient')[:20]

    context = {
        'due_today': due_today,
        
        'upcoming_followups': upcoming_followups,
    }

    return render(
        request,
        'operations/communication_center.html',
        context
    )
    
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from urllib.parse import quote


@login_required
def send_whatsapp_followup(request, followup_id):

    followup = get_object_or_404(
        AppointmentFollowUp,
        id=followup_id
    )

    phone = followup.patient.phone

    message = (
        f"Dear {followup.patient.name}, "
        f"your follow-up visit is due today. "
        f"Please contact the clinic regarding "
        f"{followup.followup_topic or 'your scheduled follow-up'}."
    )

    whatsapp_url = (
        f"https://wa.me/91{phone}"
        f"?text={quote(message)}"
    )

    return HttpResponseRedirect(
        whatsapp_url
    )