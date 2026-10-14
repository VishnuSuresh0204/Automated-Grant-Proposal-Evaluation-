"""
URL configuration for grant project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from myapp import views

urlpatterns = [
    path('django-admin/', admin.site.urls, name='django_admin'),
    path('', views.home, name='home'),
    path('applicant/', views.applicant_home, name='applicant_home'),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin_dashboard/', views.admin_home, name='admin_dashboard'),
    path('admin_home/', views.admin_home, name='admin_home_alias'),
    path('reviewer/', views.reviewr_home, name='reviewer'),
    path('reviewer_home/', views.reviewr_home, name='reviewer_home'),
    path('applicant_registration/', views.applicant_registration, name='applicant_registration'),
    path('aplicaant_reg/', views.applicant_registration, name='aplicaant_reg'),
    path('reviewer_registration/', views.reviewer_registration, name='reviewer_registration'),
    path('river_reg/', views.reviewer_registration, name='river_reg'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

