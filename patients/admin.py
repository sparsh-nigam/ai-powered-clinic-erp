from django.contrib import admin
from .models import Patient
from appointments.models import Appointment
# Register your models here.
class AppointmentInLine(admin.StackedInline):
    model = Appointment
    extra=0
    
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display=(
        'title',
        'name',
        'gender',
        'phone',
    )
    
    search_fields=(
        'title',
        'name',
        'phone',
    )
    
    inlines=[AppointmentInLine]