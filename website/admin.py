from django.contrib import admin
from .models import WebsiteSettings
# Register your models here.
@admin.register(WebsiteSettings)

class WebsiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if WebsiteSettings.objects.exists():
            return False
        return True