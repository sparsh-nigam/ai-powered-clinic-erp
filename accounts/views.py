from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from datetime import date
from django.db.models import Sum, Count, Avg, Q
from patients.models import Patient
from appointments.models import Appointment
from doctors.models import Doctor, TransferRequest
from operations.models import ( BillingSession, BillingTransaction )
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.db.models.functions import ExtractMonth, ExtractYear
import json
from django.core.serializers.json import DjangoJSONEncoder
from operations.models import PatientCondition, AppointmentFollowUp, FollowUpCondition

# Create your views here.
def login_view(request):
    
    if request.method == "POST":
        username=request.POST.get('username')
        password=request.POST.get('password')
        
        user=authenticate(
            request,
            username=username,
            password=password
        )
        
        if user is not None:
            login(request,user)
            if user.role=='SUPER_OWNER':
                return redirect('/accounts/dashboard/')
            elif user.role=='STAFF':
                return redirect('/accounts/dashboard/')
            elif user.role=='DOCTOR':
                return redirect('/accounts/dashboard/')
        
        else:
            messages.error(request,'Invalid username or password')
    return render(request, 'accounts/login.html')
@login_required(login_url='/accounts/login/')
def dashboard_view(request):
    return render(request,'dashboard/dashboard.html')


@login_required(login_url='/accounts/login/')
def overview(request):

    today = date.today()

    total_patients = Patient.objects.count()

    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).count()

    queue_waiting = Appointment.objects.filter(
        appointment_date=today,
        status='Pending'
    ).count()

    in_consultation = Appointment.objects.filter(
        appointment_date=today,
        status='In Consultation'
    ).count()
    
    today_revenue = (
        BillingTransaction.objects.filter(
            created_at__date=today,
            is_void=False
        ).aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )

    active_billing_sessions = BillingSession.objects.filter(
        session_status='Active'
    ).count()

    pending_transfers = TransferRequest.objects.filter(
        status='Pending'
    ).count()

    total_doctors = Doctor.objects.count()
    
    pending_transfer_list = (
        TransferRequest.objects.filter(
            status='Pending'
        )
        .select_related(
            'appointment__patient',
            'from_doctor',
            'to_doctor'
        )
        .order_by('-created_at')
    )
    
    doctor_snapshot = []

    for doctor in Doctor.objects.all():

        total_patients = Appointment.objects.filter(
            doctor=doctor
        ).count()

        today_patients = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today
        ).count()

        doctor_snapshot.append({
            'doctor': doctor,
            'total_patients': total_patients,
            'today_patients': today_patients,
        })
    
    doctor_snapshot = sorted(
        doctor_snapshot,
        key=lambda x: x['total_patients'],
        reverse=True
    )

    context = {

        'total_patients': total_patients,

        'today_appointments': today_appointments,

        'queue_waiting': queue_waiting,

        'in_consultation': in_consultation,

        'today_revenue': today_revenue,

        'active_billing_sessions': active_billing_sessions,

        'pending_transfers': pending_transfers,

        'total_doctors': total_doctors,
        
        'doctor_snapshot': doctor_snapshot,
        
        'pending_transfer_list': pending_transfer_list,

    }

    return render(
        request,
        'dashboard/overview.html',
        context
    )

@login_required(login_url='/accounts/login/')
def analytics(request):

    today = timezone.localdate()

    week_start = today - timedelta(days=today.weekday())

    month_start = today.replace(day=1)

    year_start = today.replace(month=1, day=1)
    
    period = request.GET.get('period', 'today')

    custom_start = request.GET.get('start_date')
    custom_end = request.GET.get('end_date')

    filter_start = today
    filter_end = today

    if period == 'yesterday':
        filter_start = today - timedelta(days=1)
        filter_end = filter_start

    elif period == 'week':
        filter_start = today - timedelta(days=6)
        filter_end = today

    elif period == 'month':
        filter_start = month_start
        filter_end = today

    elif period == 'last_month':

        first_day_this_month = today.replace(day=1)

        filter_end = first_day_this_month - timedelta(days=1)

        filter_start = filter_end.replace(day=1)

    elif period == 'year':
        filter_start = year_start
        filter_end = today

    if custom_start and custom_end:
        filter_start = custom_start
        filter_end = custom_end
        
    transaction_base = BillingTransaction.objects.filter(
        is_void=False
    )

    appointment_base = Appointment.objects.all()

    patient_base = Patient.objects.all()

    transaction_base = transaction_base.filter(
        payment_received_at__date__range=[
            filter_start,
            filter_end
        ]
    )

    appointment_base = appointment_base.filter(
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    )

    patient_base = patient_base.filter(
        created_at__date__range=[
            filter_start,
            filter_end
        ]
    )
    
    condition_base = PatientCondition.objects.filter(
        patient__created_at__date__range=[
            filter_start,
            filter_end
        ]
    )
    
    payment_base = BillingTransaction.objects.filter(
        payment_status='Paid',
        is_void=False
    )
    payment_today = payment_base.filter(
        payment_received_at__date=today
    )

    payment_week = payment_base.filter(
        payment_received_at__date__gte=week_start
    )

    payment_month = payment_base.filter(
        payment_received_at__date__gte=month_start
    )

    payment_year = payment_base.filter(
        payment_received_at__date__gte=year_start
    )
    
    def payment_breakdown(qs):
        
        return {
            'cash': qs.filter(payment_mode='Cash').count(),
            'upi': qs.filter(payment_mode='UPI').count(),
            'card': qs.filter(payment_mode='Card').count(),
        }
        
    revenue_transactions = BillingTransaction.objects.filter(
        payment_status='Paid',
        is_void=False
    ).exclude(
        transaction_type='Due Clearance'
    )

    today_revenue = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ]
        ).aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )

    weekly_revenue = (
        revenue_transactions.filter(
            payment_received_at__date__gte=week_start
        ).aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )

    monthly_revenue = (
        revenue_transactions.filter(
            payment_received_at__date__gte=month_start
        ).aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )

    yearly_revenue = (
        revenue_transactions.filter(
            payment_received_at__date__gte=year_start
        ).aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )
    
    lifetime_revenue = (
        revenue_transactions.aggregate(
            total=Sum('paid_amount')
        )['total']
        or 0
    )

    total_due_amount = (
        BillingSession.objects.filter(
            session_status='Due Pending'
        ).aggregate(
            total=Sum('total_due')
        )['total']
        or 0
    )

    active_due_sessions = (
        BillingSession.objects.filter(
            session_status='Due Pending'
        ).count()
    )

    unpaid_transactions = (
        BillingTransaction.objects.filter(
            payment_status='Pending',
            is_void=False
        ).count()
    )

    waived_consultations = (
        Appointment.objects.filter(
            payment_status='Waived'
        ).count()
    )
    
    highest_revenue_day = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ],
            payment_received_at__isnull=False
        )
        .annotate(day=TruncDate('payment_received_at'))
        .values('day')
        .annotate(revenue=Sum('paid_amount'))
        .order_by('-revenue')
        .first()
    )

    highest_revenue_month = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ],
            payment_received_at__isnull=False
        )
        .annotate(month=TruncMonth('payment_received_at'))
        .values('month')
        .annotate(revenue=Sum('paid_amount'))
        .order_by('-revenue')
        .first()
    )

    highest_revenue_year = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ],
            payment_received_at__isnull=False
        )
        .annotate(year=TruncYear('payment_received_at'))
        .values('year')
        .annotate(revenue=Sum('paid_amount'))
        .order_by('-revenue')
        .first()
    )
    
    highest_appointment_day = (
        appointment_base
        .values('appointment_date')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    highest_appointment_month = (
        appointment_base
        .annotate(
            month=ExtractMonth('appointment_date')
        )
        .values('month')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    highest_appointment_year = (
        appointment_base
        .annotate(
            year=ExtractYear('appointment_date')
        )
        .values('year')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )
    most_busy_doctor = (
        Doctor.objects
        .annotate(
            appointment_count=Count(
                'appointment',
                filter=Q(
                    appointment__appointment_date__range=[
                        filter_start,
                        filter_end
                    ]
                )
            )
        )
        .order_by('-appointment_count')
        .first()
    )
    
    most_busy_doctor_today = most_busy_doctor
    
    most_busy_doctor_month = most_busy_doctor
    
    revenue_doctor_month = (
        revenue_transactions.filter(
            payment_status='Paid',
            is_void=False,
            payment_received_at__date__gte=month_start,
            appointment__doctor__isnull=False
        )
        .values(
            'appointment__doctor__name'
        )
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('-revenue')
        .first()
    )
    
    revenue_doctor_today = (
        revenue_transactions.filter(
            payment_status='Paid',
            is_void=False,
            payment_received_at__date=today,
            appointment__doctor__isnull=False
        )
        .values(
            'appointment__doctor__name'
        )
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('-revenue')
        .first()
    )
    
    daily_revenue_trend = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ]
        )
        .annotate(
            day=TruncDate('payment_received_at')
        )
        .values('day')
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('day')
    )
    # =========================
    # PATIENT ANALYTICS
    # =========================

    total_patients = patient_base.count()

    new_patients_today = (
        Patient.objects.filter(
            created_at__date__range=[
                filter_start,
                filter_end
            ]
        ).count()
    )

    new_patients_week = (
        Patient.objects.filter(
            created_at__date__gte=week_start
        ).count()
    )

    new_patients_month = (
        Patient.objects.filter(
            created_at__date__gte=month_start
        ).count()
    )

    new_patients_year = (
        Patient.objects.filter(
            created_at__date__gte=year_start
        ).count()
    )
    
    revisit_visits = 0

    patient_appointment_stats = (
        patient_base.annotate(
            appointment_count=Count('appointment')
        )
    )
    
    revisit_patients = 0
    revisit_visits = 0
            
    for patient in patient_appointment_stats:

        if patient.appointment_count > 1:

            revisit_patients += 1

            revisit_visits += (
                patient.appointment_count - 1
            )
    
  
    retention_rate = round(
        (revisit_patients / total_patients) * 100,
        2
    ) if total_patients else 0
    # =========================
    # GENDER ANALYTICS
    # =========================

    male_patients = patient_base.filter(
        gender='M'
    ).count()

    female_patients = patient_base.filter(
            gender='F'
        ).count()
    

    other_patients = patient_base.filter(
            gender='Oth'
        ).count()
   
    
    total_gender_patients = (
        male_patients +
        female_patients +
        other_patients
    )
    
    male_percentage = round(
        (male_patients / total_gender_patients) * 100,
        2
    ) if total_gender_patients else 0

    female_percentage = round(
        (female_patients / total_gender_patients) * 100,
        2
    ) if total_gender_patients else 0

    other_percentage = round(
        (other_patients / total_gender_patients) * 100,
        2
    ) if total_gender_patients else 0

    # =========================
    # PAYMENT MODE ANALYTICS
    # =========================
    filtered_payment_data = {
            'cash': transaction_base.filter(
                payment_status='Paid',
                payment_mode='Cash'
            ).count(),

            'upi': transaction_base.filter(
                payment_status='Paid',
                payment_mode='UPI'
            ).count(),

            'card': transaction_base.filter(
                payment_status='Paid',
                payment_mode='Card'
            ).count(),
        }
    cash_payments = transaction_base.filter(
        payment_status='Paid',
        payment_mode='Cash'
    ).count()

    upi_payments = transaction_base.filter(
        payment_status='Paid',
        payment_mode='UPI'
    ).count()

    card_payments = transaction_base.filter(
        payment_status='Paid',
        payment_mode='Card'
    ).count()
    
    total_payment_transactions = (
        cash_payments +
        upi_payments +
        card_payments
    )
    
    cash_percentage = round(
        (cash_payments / total_payment_transactions) * 100,
        2
    ) if total_payment_transactions else 0
    
    upi_percentage = round(
        (upi_payments / total_payment_transactions) * 100,
        2
    ) if total_payment_transactions else 0
    
    card_percentage = round(
        (card_payments / total_payment_transactions) * 100,
        2
    ) if total_payment_transactions else 0

    # =========================
    # WAIVER ANALYTICS
    # =========================

    waiver_patients = (
        appointment_base.filter(
            payment_status='Waived'
        ).count()
    )
    
    total_appointments = appointment_base.count()
    
    waiver_percentage = round(
        (waiver_patients / total_appointments) * 100,
        2
    ) if total_appointments else 0

    # =========================
    # AGE ANALYTICS
    # =========================

    average_age = (
        patient_base.aggregate(
            avg=Avg('age')
        )['avg']
        or 0
    )
    
    all_ages = patient_base.values_list(
        'age',
        flat=True
    )

    age_0_5 = 0
    age_6_10 = 0
    age_11_15 = 0
    age_16_20 = 0
    age_21_25 = 0
    age_26_30 = 0
    age_31_35 = 0
    age_36_40 = 0
    age_41_45 = 0
    age_46_50 = 0
    age_51_55 = 0
    age_56_60 = 0
    age_61_65 = 0
    age_66_70 = 0
    age_71_75 = 0
    age_76_80 = 0
    age_81_85 = 0
    age_86_90 = 0
    age_91_95 = 0
    age_96_plus = 0

    for age in all_ages:

        if age is None:
            continue

        if 0 <= age <= 5:
            age_0_5 += 1

        elif 6 <= age <= 10:
            age_6_10 += 1

        elif 11 <= age <= 15:
            age_11_15 += 1

        elif 16 <= age <= 20:
            age_16_20 += 1

        elif 21 <= age <= 25:
            age_21_25 += 1

        elif 26 <= age <= 30:
            age_26_30 += 1

        elif 31 <= age <= 35:
            age_31_35 += 1

        elif 36 <= age <= 40:
            age_36_40 += 1

        elif 41 <= age <= 45:
            age_41_45 += 1

        elif 46 <= age <= 50:
            age_46_50 += 1

        elif 51 <= age <= 55:
            age_51_55 += 1

        elif 56 <= age <= 60:
            age_56_60 += 1

        elif 61 <= age <= 65:
            age_61_65 += 1

        elif 66 <= age <= 70:
            age_66_70 += 1

        elif 71 <= age <= 75:
            age_71_75 += 1

        elif 76 <= age <= 80:
            age_76_80 += 1

        elif 81 <= age <= 85:
            age_81_85 += 1

        elif 86 <= age <= 90:
            age_86_90 += 1

        elif 91 <= age <= 95:
            age_91_95 += 1

        else:
            age_96_plus += 1
    
    doctor_revenue = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ],
            appointment__doctor__isnull=False
        )
        .values(
            'appointment__doctor__name'
        )
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('-revenue')
    )
    
    patient_growth_trend = (
        patient_base
        .annotate(
            day=TruncDate('created_at')
        )
        .values('day')
        .annotate(
            patients=Count('id')
        )
        .order_by('day')
    )
    monthly_revenue_trend = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ]
        )
        .annotate(
            month=TruncMonth('payment_received_at')
        )
        .values('month')
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('month')
    )
    yearly_revenue_trend = (
        revenue_transactions.filter(
            payment_received_at__date__range=[
                filter_start,
                filter_end
            ]
        )
        .annotate(
            year=TruncYear('payment_received_at')
        )
        .values('year')
        .annotate(
            revenue=Sum('paid_amount')
        )
        .order_by('year')
    )
    monthly_patient_growth = (
        patient_base
        .annotate(
            month=TruncMonth('created_at')
        )
        .values('month')
        .annotate(
            patients=Count('id')
        )
        .order_by('month')
    )   
    yearly_patient_growth = (
        patient_base
        .annotate(
            year=TruncYear('created_at')
        )
        .values('year')
        .annotate(
            patients=Count('id')
        )
        .order_by('year')
    ) 
    
    top_revenue_doctors = doctor_revenue[:5]
    
    doctor_chart_data = [

        {
            'doctor':
                item['appointment__doctor__name'],

            'revenue':
                float(item['revenue'])
        }

        for item in top_revenue_doctors

    ]

    most_revenue_doctor = doctor_revenue.first()
    
    daily_revenue_chart = [
        {
            'label': item['day'].strftime('%d %b'),
            'value': float(item['revenue'])
        }
        for item in daily_revenue_trend
    ]

    monthly_revenue_chart = [
        {
            'label': item['month'].strftime('%b %Y'),
            'value': float(item['revenue'])
        }
        for item in monthly_revenue_trend
    ]

    yearly_revenue_chart = [
        {
            'label': item['year'].strftime('%Y'),
            'value': float(item['revenue'])
        }
        for item in yearly_revenue_trend
    ]
    
    patient_growth_chart = [
        {
            'label': item['day'].strftime('%d %b'),
            'value': item['patients']
        }
        for item in patient_growth_trend
    ]

    monthly_patient_chart = [
        {
            'label': item['month'].strftime('%b %Y'),
            'value': item['patients']
        }
        for item in monthly_patient_growth
    ]

    yearly_patient_chart = [
        {
            'label': item['year'].strftime('%Y'),
            'value': item['patients']
        }
        for item in yearly_patient_growth
    ]
    
    # =========================
    # CONDITION ANALYTICS
    # =========================

    condition_stats = (
        condition_base
        .values('condition')
        .annotate(total=Count('patient', distinct=True))
        .order_by('-total')
    )
    
    condition_chart_labels = []
    condition_chart_values = []

    for row in condition_stats:

        condition_chart_labels.append(
            row['condition']
        )

        condition_chart_values.append(
            row['total']
        )
    # =========================
    # CONDITION VISIT ANALYTICS
    # =========================

    diabetes_visits = Appointment.objects.filter(
        patient__condition_records__condition='Diabetes',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    hypertension_visits = Appointment.objects.filter(
        patient__condition_records__condition='Hypertension',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    kidney_visits = Appointment.objects.filter(
        patient__condition_records__condition='Kidney Disease',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    liver_visits = Appointment.objects.filter(
        patient__condition_records__condition='Liver Disease',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    thyroid_visits = Appointment.objects.filter(
        patient__condition_records__condition='Thyroid',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    asthma_visits = Appointment.objects.filter(
        patient__condition_records__condition='Asthma',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()

    heart_visits = Appointment.objects.filter(
        patient__condition_records__condition='Heart Disease',
        appointment_date__range=[
            filter_start,
            filter_end
        ]
    ).count()
    
    
    
    condition_visit_chart_data = [
        diabetes_visits,
        hypertension_visits,
        kidney_visits,
        liver_visits,
        thyroid_visits,
        asthma_visits,
        heart_visits,
    ]
    
    # =========================
    # FOLLOWUP COMBINATION ANALYTICS
    # =========================

    followup_base = AppointmentFollowUp.objects.filter(
        created_at__date__range=[
            filter_start,
            filter_end
        ]
    )

    combination_counter = {}

    for followup in followup_base:

        conditions = list(
            followup.conditions.values_list(
                'condition_name',
                flat=True
            )
        )

        conditions.sort()

        combination_name = " + ".join(
            conditions
        )

        if not combination_name:
            continue

        combination_counter[
            combination_name
        ] = (
            combination_counter.get(
                combination_name,
                0
            ) + 1
        )
        
    sorted_combinations = sorted(
        combination_counter.items(),
        key=lambda x: x[1],
        reverse=True
    )

    followup_chart_labels = [
        item[0]
        for item in sorted_combinations[:10]
    ]

    followup_chart_values = [
        item[1]
        for item in sorted_combinations[:10]
    ]
    
    context = {
        'filtered_payment_data':
        json.dumps(filtered_payment_data),
        'today_revenue': today_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'lifetime_revenue': lifetime_revenue,
        'total_due_amount': total_due_amount,
        'active_due_sessions': active_due_sessions,
        'unpaid_transactions': unpaid_transactions,
        'waived_consultations': waived_consultations,
        'highest_revenue_day': highest_revenue_day,
        'highest_revenue_month': highest_revenue_month,
        'highest_revenue_year': highest_revenue_year,
        'highest_appointment_day': highest_appointment_day,
        'highest_appointment_month': highest_appointment_month,
        'highest_appointment_year': highest_appointment_year,
        'most_busy_doctor': most_busy_doctor,
        'most_busy_doctor_today': most_busy_doctor_today,
        'total_patients': total_patients,
        'most_busy_doctor_month': most_busy_doctor_month,
        'new_patients_today': new_patients_today,
        'new_patients_week': new_patients_week,
        'new_patients_month': new_patients_month,
        'new_patients_year': new_patients_year,
        'revisit_patients': revisit_patients,
        'revisit_visits': revisit_visits,
        'retention_rate': retention_rate,
        'male_patients': male_patients,
        'female_patients': female_patients,
        'other_patients': other_patients,
        'total_gender_patients': total_gender_patients,

        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'other_percentage': other_percentage,

        'cash_payments': cash_payments,
        'upi_payments': upi_payments,
        'card_payments': card_payments,
        'total_payment_transactions': total_payment_transactions,

        'cash_percentage': cash_percentage,
        'upi_percentage': upi_percentage,
        'card_percentage': card_percentage,

        'waiver_patients': waiver_patients,
        'total_appointments': total_appointments,
        'waiver_percentage': waiver_percentage,

        'average_age': average_age,
        
        'most_revenue_doctor': most_revenue_doctor,
        'top_revenue_doctors': top_revenue_doctors,
        'revenue_doctor_month': revenue_doctor_month,
        'revenue_doctor_today': revenue_doctor_today,
        'daily_revenue_trend': daily_revenue_trend,
        'doctor_chart_data':
            json.dumps(
                doctor_chart_data,
                cls=DjangoJSONEncoder
            ),
        
        'age_0_5': age_0_5,
        'age_6_10': age_6_10,
        'age_11_15': age_11_15,
        'age_16_20': age_16_20,
        'age_21_25': age_21_25,
        'age_26_30': age_26_30,
        'age_31_35': age_31_35,
        'age_36_40': age_36_40,
        'age_41_45': age_41_45,
        'age_46_50': age_46_50,
        'age_51_55': age_51_55,
        'age_56_60': age_56_60,
        'age_61_65': age_61_65,
        'age_66_70': age_66_70,
        'age_71_75': age_71_75,
        'age_76_80': age_76_80,
        'age_81_85': age_81_85,
        'age_86_90': age_86_90,
        'age_91_95': age_91_95,
        'age_96_plus': age_96_plus,
        
        'patient_growth_trend': patient_growth_trend,
        'monthly_revenue_trend': monthly_revenue_trend,
        'yearly_revenue_trend': yearly_revenue_trend,

        'monthly_patient_growth': monthly_patient_growth,
        'yearly_patient_growth': yearly_patient_growth,
        
        'daily_revenue_chart':
            json.dumps(
                daily_revenue_chart,
                cls=DjangoJSONEncoder
            ),

        'monthly_revenue_chart':
            json.dumps(
                monthly_revenue_chart,
                cls=DjangoJSONEncoder
            ),

        'yearly_revenue_chart':
            json.dumps(
                yearly_revenue_chart,
                cls=DjangoJSONEncoder
            ),
            
        'patient_growth_chart':
            json.dumps(
                patient_growth_chart,
                cls=DjangoJSONEncoder
            ),

        'monthly_patient_chart':
            json.dumps(
                monthly_patient_chart,
                cls=DjangoJSONEncoder
            ),

        'yearly_patient_chart':
            json.dumps(
                yearly_patient_chart,
                cls=DjangoJSONEncoder
            ),
    
        'selected_period': period,
        
        'condition_stats': condition_stats,

        'condition_chart_labels':
            json.dumps(
                condition_chart_labels
            ),

        'condition_chart_values':
            json.dumps(
                condition_chart_values
            ),

        'diabetes_visits': diabetes_visits,
        'hypertension_visits': hypertension_visits,
        'kidney_visits': kidney_visits,
        'liver_visits': liver_visits,
        'thyroid_visits': thyroid_visits,
        'asthma_visits': asthma_visits,
        'heart_visits': heart_visits,

        'condition_visit_chart_data':
            json.dumps(
                condition_visit_chart_data
            ),
            
        'followup_chart_labels':
            json.dumps(
                followup_chart_labels
            ),

        'followup_chart_values':
            json.dumps(
                followup_chart_values
            ),
    }
    
    
    return render(
        request,
        'dashboard/analytics.html',
        context
    )
def user_roles(request):
    return render(request,'dashboard/user_roles.html')


def logout_view(request):

    logout(request)

    return redirect('login')