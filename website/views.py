from django.shortcuts import render
from .models import WebsiteSettings

# Create your views here.
def home(request):
    settings=WebsiteSettings.objects.first()
    context={
        'settings':settings
    }
    return render(request,'website/home.html',context)