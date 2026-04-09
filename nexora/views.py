from django.shortcuts import render, redirect
from home.models import User
from django.contrib import messages
import random
from django.core.mail import send_mail
import re
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

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

        # Find user by email or username
        user = User.objects.filter(email=identifier).first()
        if not user:
            user = User.objects.filter(username=identifier).first()

        if user and user.check_password(password):
            # Store user id in session
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

            # Send OTP email using API Backend
            send_mail(
                subject="Nexora Password Reset OTP",
                message=f"Hello,\n\nYour OTP for password reset is: {otp}\n\nValid for 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL, # CHANGED: Uses API sender
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

        # cleanup session
        request.session.pop('otp', None)
        request.session.pop('reset_email', None)

        messages.success(request, "Password reset successful!")
        return redirect('login')

    return render(request, "nexora/change-pass.html")

# Step 1: Send OTP and show OTP page
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

        # Validate passwords
        if signup_data['password'] != signup_data['password2']:
            messages.warning(request, "Passwords don't match")
            return redirect('signup')

        # Validate username
        if User.objects.filter(username=signup_data['username']).exists():
            messages.warning(request, "Username already exists")
            return redirect('signup')
        if User.objects.filter(email=signup_data['email']).exists():
            messages.warning(request, "Email already exists")
            return redirect('signup')
        if not re.match(USERNAME_REGEX, signup_data['username']):
            messages.warning(request, "Username can only contain letters, numbers, and underscores.")
            return redirect('signup')

        # Generate OTP
        otp = random.randint(100000, 999999)

        # Send OTP email using API Backend
        send_mail(
            subject="Nexora Account Verification OTP",
            message=f"Hello,\n\nYour OTP for Nexora signup is: {otp}\n\nValid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL, # CHANGED: Uses API sender
            recipient_list=[signup_data['email']],
            fail_silently=False
        )

        # Store signup data and OTP in session
        request.session['signup_data'] = signup_data
        request.session['otp'] = str(otp)
        request.session.set_expiry(450)  # 7.5 minutes

        return render(request, "nexora/otp.html")

    return render(request, "nexora/signup.html")


# Step 2: Verify OTP and create user
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
                try:
                    file_content = default_storage.open(profile_path).read()
                    final_path = default_storage.save(f"images/{profile_path.split('/')[-1]}", ContentFile(file_content))
                except:
                    final_path = 'images/default.png'
            else:
                final_path = 'images/default.png'

            # Create user
            bio = signup_data.get('bio', '')
            bio = bio.replace('\r\n', '\n').replace('\r', '\n')
            bio = "\n".join(line.strip() for line in bio.split("\n") if line.strip())
            user = User(
                name=signup_data['name'],
                email=signup_data['email'],
                username=signup_data['username'],
                phone=signup_data['phone'],
                dob=signup_data['dob'],
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