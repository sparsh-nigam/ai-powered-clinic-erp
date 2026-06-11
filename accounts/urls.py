from django.urls import path
from . import views

urlpatterns = [
    path('login/',views.login_view,name='login'),
    
    path('logout/',views.logout_view, name='logout'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    path('user_roles/', views.user_roles, name="user_roles"),
    
    path(
        'overview/',
        views.overview,
        name='overview'
    ),

    path(
        'analytics/',
        views.analytics,
        name='analytics'
    ),
]