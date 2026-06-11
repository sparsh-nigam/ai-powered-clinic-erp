from django.urls import path
from .views import prescription_print

urlpatterns = [
    path(
        'prescription-print/<int:appointment_id>/',
        prescription_print,
        name='prescription_print'
    ),
]