
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from myapp import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Django built-in admin
    path('django-admin/', admin.site.urls, name='django_admin'),

    # Login and logout
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # Dashboards — preserve existing URL names
    path('applicant/', views.applicant_home, name='applicant_home'),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin_dashboard/', views.admin_home, name='admin_dashboard'),
    path('admin_home/', views.admin_home, name='admin_home_alias'),
    path('reviewer/', views.reviewr_home, name='reviewer'),
    path('reviewer_home/', views.reviewr_home, name='reviewer_home'),

    # Registration — preserve existing aliases
    path(
        'applicant_registration/',
        views.applicant_registration,
        name='applicant_registration',
    ),
    path(
        'aplicaant_reg/',
        views.applicant_registration,
        name='aplicaant_reg',
    ),
    path(
        'reviewer_registration/',
        views.reviewer_registration,
        name='reviewer_registration',
    ),
    path(
        'river_reg/',
        views.reviewer_registration,
        name='river_reg',
    ),

    # Profile and user management
    path('profile/', views.user_profile, name='user_profile'),
    path('admin/users/', views.view_users, name='view_users'),

    # Grant categories
    path('categories/', views.grant_categories, name='grant_categories'),
    path(
        'admin/categories/add/',
        views.add_grant_category,
        name='add_grant_category',
    ),
    path(
        'admin/categories/manage/',
        views.manage_categories,
        name='manage_categories',
    ),
    path(
        'admin/categories/<int:category_id>/edit/',
        views.edit_grant_category,
        name='edit_grant_category',
    ),
    path(
        'admin/categories/<int:category_id>/delete/',
        views.delete_grant_category,
        name='delete_grant_category',
    ),

    # Applicant proposals
    path(
        'proposals/submit/',
        views.submit_proposal,
        name='submit_proposal',
    ),
    path('proposals/my/', views.my_proposals, name='my_proposals'),
    path(
        'proposals/<int:proposal_id>/',
        views.proposal_details,
        name='proposal_details',
    ),

    # NLP analysis
    path(
        'admin/proposals/<int:proposal_id>/analyze/',
        views.analyze_proposal,
        name='analyze_proposal',
    ),
    path(
        'proposals/<int:proposal_id>/analysis/<int:analysis_id>/',
        views.proposal_analysis_details,
        name='proposal_analysis_details',
    ),

    # Admin proposal management
    path('admin/proposals/', views.admin_proposals, name='admin_proposals'),
    path(
        'admin/proposals/<int:proposal_id>/status/',
        views.update_proposal_status,
        name='update_proposal_status',
    ),

    # Evaluation criteria
    path('admin/criteria/', views.manage_criteria, name='manage_criteria'),
    path(
        'admin/criteria/add/',
        views.add_criterion,
        name='add_criterion',
    ),
    path(
        'admin/criteria/<int:criterion_id>/edit/',
        views.edit_criterion,
        name='edit_criterion',
    ),
    path(
        'admin/criteria/<int:criterion_id>/delete/',
        views.delete_criterion,
        name='delete_criterion',
    ),

    # Reviewer assignments
    path(
        'admin/proposals/<int:proposal_id>/assign/',
        views.assign_reviewer,
        name='assign_reviewer',
    ),
    path(
        'reviewer/assigned/',
        views.assigned_proposals,
        name='assigned_proposals',
    ),
    path(
        'reviewer/proposals/<int:proposal_id>/evaluate/',
        views.evaluate_proposal,
        name='evaluate_proposal',
    ),

    # Evaluation reports
    path(
        'admin/evaluations/',
        views.view_evaluations,
        name='view_evaluations',
    ),
    path(
        'admin/proposals/<int:proposal_id>/evaluations/',
        views.proposal_evaluations,
        name='proposal_evaluations',
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
