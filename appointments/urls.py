from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.appointments,
        name='appointments'
    ),

    path(
        'appointment-success/<int:id>/',
        views.appointment_success,
        name='appointment_success'
    ),

    path(
        'search-patient/',
        views.search_patient,
        name='search_patient'
    ),

]