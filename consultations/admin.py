from django.contrib import admin
from .models import ConsultationRecord, TreatmentItem


@admin.register(ConsultationRecord)
class ConsultationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'appointment',
        'status',
        'followup_instruction',
        'created_at'
    )

    list_filter = (
        'status',
        'created_at'
    )

    search_fields = (
        'appointment__patient__name',
        'appointment__doctor__name',
        'diagnosis'
    )


@admin.register(TreatmentItem)
class TreatmentItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'consultation_record',
        'item_type',
        'name',
        'display_order'
    )

    list_filter = (
        'item_type',
    )

    search_fields = (
        'name',
    )