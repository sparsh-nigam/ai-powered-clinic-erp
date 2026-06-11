from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.patients,
        name='patients'
    ),

    path('patient/<int:pk>/history/', views.patient_history, name='patient_history'),
    
    path('patient/<int:pk>/edit/', views.edit_patient, name='edit_patient'),

    path('add/', views.add_patient, name='add_patient'),
    
    path('followup/<int:appointment_id>/', views.save_followup, name='save_followup'),
    
    path(
        'condition/add/<int:patient_id>/',
        views.add_patient_condition,
        name='add_patient_condition'
    ),

    path(
        'condition/delete/<int:condition_id>/',
        views.delete_patient_condition,
        name='delete_patient_condition'
    ),
]