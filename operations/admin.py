from django.contrib import admin
from .models import PatientCondition, AppointmentFollowUp, MessageTemplate

admin.site.register(PatientCondition)
admin.site.register(AppointmentFollowUp)
admin.site.register(MessageTemplate)