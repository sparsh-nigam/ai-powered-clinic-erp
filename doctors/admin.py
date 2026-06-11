from django.contrib import admin
from .models import Doctor, TransferRequest
from appointments.models  import  Appointment

class AppointmentInline(admin.TabularInline):
    model=Appointment
    extra=0

@admin.register(Doctor)

class DoctorAdmin(admin.ModelAdmin):
    list_display=(
        'name',
        'specialization',
        'phone',
        'experience',
    )
    
    search_fields=(
        'name',
        'specialization',
    )
    
    list_filter=(
        'specialization',
    )
    
    inlines=[AppointmentInline]
    
admin.site.register(TransferRequest)