from django.urls import path
from . import views

urlpatterns = [
    path('', views.doctor_dashboard, name='doctor_dashboard'),
    
    path('schedules/', views.schedules, name='schedules'),
    
    path(
        'my-patients/',
        views.my_patients,
        name='my_patients'
    ),

    path(
        'my-patient-history/<int:patient_id>/',
        views.my_patient_history,
        name='my_patient_history'
    ),
]