"""
URL configuration for clinic_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings            #---|
from django.conf.urls.static import static  #---|--->both are added for Patient action center to add media (photo upload and so)
from django.shortcuts import redirect

def home_redirect(request):

    if request.user.is_authenticated:

        return redirect(

            'dashboard'

        )



    return redirect(

        'login'

    )
    
    
urlpatterns = [
    
    path(

        '',

        home_redirect

    ),
    path('admin/', admin.site.urls),
    
    path('',include('website.urls')),
    
    path('accounts/',include('accounts.urls')),
    
    path(
        'operations/',
        include('operations.urls')
    ),
    
    path(
        'appointments/',
        include('appointments.urls')
    ),
    
    path(
        'patients/',
        include('patients.urls')
    ),
    
    path('doctor/', include('doctors.urls')),
    
    path(
        'consultations/',
        include('consultations.urls')
    ),
    
    
]
if settings.DEBUG:

    urlpatterns += static(

        settings.MEDIA_URL,

        document_root=settings.MEDIA_ROOT

    )