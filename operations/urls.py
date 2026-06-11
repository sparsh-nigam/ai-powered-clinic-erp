from django.urls import path
from . import views

urlpatterns = [

    path(
        'queue-management/',
        views.queue_management,
        name='queue_management'
    ),
    
    path(

        'action-center/<int:id>/',

        views.action_center,

        name='action_center'

    ),
    
    path(

        'billing/<int:id>/',

        views.billing,

        name='billing'

    ),
    
    path(
        'delete-billing/<int:id>/',
        views.delete_billing_transaction,
        name='delete_billing_transaction'
    ),
    
    path(

        'billing-history/<str:patient_id>/',

        views.billing_history,

        name='billing_history'

    ),
    
    path(

        'final-invoice/<int:session_id>/',

        views.final_invoice,

        name='final_invoice'

    ),
    
    path(

        'download-invoice/<int:session_id>/',

        views.download_invoice_pdf,

        name='download_invoice_pdf'

    ),
    
    path(
        'communication-center/',
        views.communication_center,
        name='communication_center'
    ),
    
    path(
        'followup-whatsapp/<int:followup_id>/',
        views.send_whatsapp_followup,
        name='send_whatsapp_followup'
    ),

]