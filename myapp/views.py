from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login ,logout as auth_logout
from django.contrib.auth.decorators import login_required

from myapp.models import *

def home(request):
    return render(request, "index.html")

def applicant_home(request):
    proposals_count = 3
    context = {
        'total_proposals': proposals_count,
        'username': request.session.get('username', 'Applicant'),
    }
    return render(request, "applicant/index.html", context)

def admin_home(request):
    total_reviewers_db = Login.objects.filter(user_type='Reviewer').count()
    total_applicants_db = Login.objects.filter(user_type='Applicant').count()

    context = {
        'total_proposals': 148,
        'total_reviewers': total_reviewers_db if total_reviewers_db > 0 else 42,
        'total_applicants': total_applicants_db if total_applicants_db > 0 else 89,
        'total_screened': 136,
        'total_funds': "4.85M",
        'status_counts': {
            'Screening': 12,
            'Reviewing': 64,
            'Consensus': 46,
            'Awarded': 26,
        }
    }
    return render(request, "admin/admin_home.html", context)

def reviewr_home(request):
    context = {
        'username': request.session.get('username', 'Reviewer'),
        'assigned_count': 4,
        'completed_count': 2,
    }
    return render(request, "reviwer/index.html", context)





def applicant_registration(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        organization = request.POST.get('organization', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        profile_image = request.FILES.get('profile_image')

        if not all([name, username, email, password, confirm_password]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('applicant_registration')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('applicant_registration')

        if Login.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('applicant_registration')

        if Login.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('applicant_registration')

        user = Login.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type='Applicant'
        )

        ApplicantRegistration.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            address=address,
            organization=organization,
            profile_image=profile_image
        )

        messages.success(
            request, 'Applicant registration successful. Please log in.'
        )
        return redirect('login')

    return render(request, 'applicant_registration.html')


def reviewer_registration(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        organization = request.POST.get('organization', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        profile_image = request.FILES.get('profile_image')

        if not all([name, username, email, password, confirm_password]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('reviewer_registration')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('reviewer_registration')

        if Login.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('reviewer_registration')

        if Login.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('reviewer_registration')

        user = Login.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type='Reviewer'
        )

        ReviewerRegistration.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            address=address,
            organization=organization,
            profile_image=profile_image
        )

        messages.success(
            request, 'Reviewer registration successful. Please log in.'
        )
        return redirect('login')

    return render(request, 'reviewer_registration.html')


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_active:
            if user.user_type not in ['Admin', 'Applicant', 'Reviewer']:
                messages.error(request, 'Invalid user role.')
                return redirect('login')

            auth_login(request, user)

            request.session['userid'] = user.id
            request.session['username'] = user.username
            request.session['usertype'] = user.user_type

            if user.user_type == 'Admin':
                return redirect('/admin/')
            elif user.user_type == 'Applicant':
                return redirect('/applicant/')
            elif user.user_type == 'Reviewer':
                return redirect('/reviewer/')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')

def logout(request):
    auth_logout(request)
    request.session.flush()
    return redirect('/login')