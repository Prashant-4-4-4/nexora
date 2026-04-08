from django.shortcuts import render, redirect
from home.models import User
from django.contrib import messages
import random
from django.core.mail import send_mail
import re
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

USERNAME_REGEX = r'^[a-zA-Z0-9_]+$'

def index(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return render(request, "nexora/index.html")
    
    return redirect('home')

def login(request):
    if request.method == "POST":
        identifier = request.POST.get('identifier').strip()
        password = request.POST.get('pass').strip()

        user = User.objects.filter(email=identifier).first()
        if not user:
            user = User.objects.filter(username=identifier).first()

        if user and user.check_password(password):
            request.session['user_id'] = user.id
            messages.success(request, "Login successful!")
            return redirect('home')
        else:
            messages.warning(request, "Username/email or password incorrect.")
            return redirect('login')

    return render(request, "nexora/login.html")

def forget_password(request):
    if request.method == "POST" :
        email = request.POST.get('email') 
        user = User.objects.filter(email=email).first()
        if user:
            otp = random.randint(100000, 999999)

            send_mail(
                subject="Nexora Password Reset OTP",
                message=f"""Hello,

            We received a request to reset the password for your Nexora account. To proceed, please use the OTP below:

            OTP: {otp}

            This OTP is valid for the next 10 minutes. Please do not share it with anyone for your account security.

            If you did not request a password reset, please ignore this email.

            Best regards,
            The Nexora Team
            """,
                from_email="supportnexora@gmail.com",
                recipient_list=[email],
                fail_silently=False
            )

            request.session['reset_email'] = email
            request.session['otp'] = str(otp)
            request.session.set_expiry(450)

            messages.success(request, "OTP sent to your given mail address")
            return render(request, 'nexora/forget-pass.html', {
                'otp_sent': True,
                'disable': True,
                'user': user
            })

        else:
            messages.warning(request, "Email not found")
            return redirect(request.path)
        
    return render (request,'nexora/forget-pass.html', {'otp_sent': False,'disable': False})

def verify_reset_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get('enteredOtp')
        session_otp = request.session.get('otp')
        email = request.session.get('reset_email')

        if not session_otp or not email:
            messages.warning(request, "Session expired.")
            return redirect('forgot-pass')

        if entered_otp == session_otp:
            return redirect('change_password')
        else:
            messages.warning(request, "Invalid OTP")
            return redirect(request.path)

    return render(request, "nexora/forget-pass.html")

def change_password(request):
    email = request.session.get('reset_email')

    if not email:
        return redirect('forget-password')

    user = User.objects.filter(email=email).first()

    if request.method == "POST":
        new_pass = request.POST.get('newpass')
        confirm_pass = request.POST.get('confirmpass')

        if new_pass != confirm_pass:
            messages.warning(request, "Passwords do not match")
            return redirect(request.path)

        user.set_password(new_pass)
        user.save()

        request.session.pop('otp', None)
        request.session.pop('reset_email', None)

        messages.success(request, "Password reset successful!")
        return redirect('login')

    return render(request, "nexora/change-pass.html")

def signup(request):
    if request.method == "POST":
        profile_file = request.FILES.get('profile_img')

        signup_data = {
            'name': request.POST.get('name').strip(),
            'email': request.POST.get('email').strip(),
            'username': request.POST.get('username').strip(),
            'phone': request.POST.get('phone').strip(),
            'dob': request.POST.get('dob'),
            'password': request.POST.get('createpass').strip(),
            'password2': request.POST.get('confirmpass').strip(),
            'is_private' : request.POST.get('is_private') == 'on',
            'bio' : request.POST.get('bio'),
            'gender' : request.POST.get('gender')
        }

        if profile_file:
            temp_path = default_storage.save(f"temp/{profile_file.name}", profile_file)
            signup_data['profile_image_path'] = temp_path
        else:
            signup_data['profile_image_path'] = None

        if signup_data['password'] != signup_data['password2']:
            messages.warning(request, "Passwords don't match")
            return redirect('signup')

        if User.objects.filter(username=signup_data['username']).exists():
            messages.warning(request, "Username already exists")
            return redirect('signup')
        if User.objects.filter(email=signup_data['email']).exists():
            messages.warning(request, "Email already exists")
            return redirect('signup')
        if not re.match(USERNAME_REGEX, signup_data['username']):
            messages.warning(request, "Username can only contain letters, numbers, and underscores.")
            return redirect('signup')

        otp = random.randint(100000, 999999)

        try:
            send_mail(
                subject="Nexora Account Verification OTP",
                message=f"""Hello,

            Thank you for signing up for Nexora! To complete your account registration, please use the OTP provided below:

            OTP: {otp}

            This OTP is valid for the next 10 minutes. Please do not share it with anyone for your account security.

            If you did not request this, please ignore this email.

            Best regards,
            The Nexora Team
            """,
                from_email="supportnexora@gmail.com",
                recipient_list=[signup_data['email']],
                fail_silently=False,
                timeout=15
            )
        except Exception as e:
            messages.error(request, f"Error sending email: {str(e)}")
            return redirect('signup')

        request.session['signup_data'] = signup_data
        request.session['otp'] = str(otp)
        request.session.set_expiry(450)

        return render(request, "nexora/otp.html")

    return render(request, "nexora/signup.html")

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get('enteredOtp')
        session_otp = request.session.get('otp')
        signup_data = request.session.get('signup_data')

        if not signup_data or not session_otp:
            messages.warning(request, "Session expired. Please try signup again.")
            return redirect('signup')

        if entered_otp == session_otp:
            profile_path = signup_data.get('profile_image_path')
            if profile_path:
                file_content = default_storage.open(profile_path).read()
                final_path = default_storage.save(f"images/{profile_path.split('/')[-1]}", ContentFile(file_content))
            else:
                final_path = 'images/default.png'

            bio = signup_data.get('bio', '')
            bio = bio.replace('\r\n', '\n').replace('\r', '\n')
            bio = "\n".join(line.strip() for line in bio.split("\n") if line.strip())
            
            user = User(
                name=signup_data['name'],
                email=signup_data['email'],
                username=signup_data['username'],
                phone=signup_data['phone'],
                dob=signup_data['dob'] if signup_data['dob'] else None,
                is_private = signup_data['is_private'],
                gender = signup_data['gender'],
                bio = bio,
                profile_image=final_path
            )
            user.set_password(signup_data['password'])
            user.save()

            request.session['user_id'] = user.id

            request.session.pop('signup_data')
            request.session.pop('otp')

            messages.success(request, "Signup successful!")
            return redirect('home')
        else:
            messages.warning(request, "OTP does not match. Try again.")
            return render(request, "nexora/otp.html")

    return redirect('signup')