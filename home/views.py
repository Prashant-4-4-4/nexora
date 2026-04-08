from django.shortcuts import render, redirect,  get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from home.models import User,Message,Conversation, Post, PostImage, PostVideo, Like, Comment
from django.db.models import Q
from datetime import date
from django.contrib.auth import logout

def home(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    
    user = User.objects.get(id=user_id)

    posts = Post.objects.all().order_by("-id").prefetch_related('likes')

    visible_posts = []
    for post in posts:
        post.is_liked = post.likes.filter(user=user).exists()
        post.is_follower = user in post.user.followers.all()
        if not post.user.is_private or post.is_follower or post.user == user:
            visible_posts.append(post)

    return render(request, "home/home.html", {
        "user": user,
        "posts": visible_posts,
    })

def search(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    users = []
    is_user = False
    if request.method == 'POST':
        query = request.POST.get("search")
        users = User.objects.filter(Q(username__icontains=query))
        is_user = True

    return render(request, "home/search.html", {"users": users , "is_user" : is_user})



def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def profile(request, username):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)
    profile_user = User.objects.get(username=username)

   
    is_owner = user == profile_user
    is_follower = profile_user.followers.filter(id=user.id).exists()

    can_view_posts = (
        not profile_user.is_private or
        is_owner or
        is_follower
    )
    user_age = calculate_age(user.dob) if user.dob else 0
    if request.method == "POST":
        if user in profile_user.requests.all() or user in profile_user.followers.all():
            profile_user.requests.remove(user)     
            profile_user.followers.remove(user) 
        else:
            profile_user.requests.add(user)     

        return redirect(request.path)

    context = {
        "user": user,
        "profile_user": profile_user,
        "is_owner": is_owner,
        "is_follower": is_follower,
        "can_view_posts": can_view_posts,
        "user_age" : user_age,
    }

    return render(request, "home/profile.html", context)


def request(request):
    
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)

    
    incoming_requests = user.requests.all() 

    # Handle Accept / Reject actions
    if request.method == "POST":
        req_user_id = request.POST.get("request_user_id")  # hidden input from form
        action = request.POST.get("action")
        req_user = User.objects.get(id=req_user_id)

        if action == "accept":
            # Add follower/following
            user.followers.add(req_user)   # user gains follower
            req_user.following.add(user)   # sender gains following
            # Remove from requests
            user.requests.remove(req_user)

        elif action == "reject":
            # Just remove the request
            user.requests.remove(req_user)

        return redirect(request.path)  # reload page to see updated requests

    return render(request, "home/request.html", {"user": user, "incoming_requests": incoming_requests})


def logout(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('/')
    
    # Remove user_id from session
    if 'user_id' in request.session:
        del request.session['user_id']
    
    return redirect('/')


def message_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    sender = get_object_or_404(User, id=user_id)
    chat_data = []
    conversations = Conversation.objects.filter(participants=sender)
    for convo in conversations:
        receivers = convo.participants.exclude(id=sender.id)
        last_message = convo.messages.order_by('-timestamp').first()  # newest message
        chat_data.append({
            "receivers": receivers,
            "last_message": last_message
        })

    chat_data.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else 0, reverse=True)
    return render(request, "home/messagelst.html", {
        "chat_data": chat_data,
        "sender": sender
    })



def can_message(request, username):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    # Get sender and receiver
    sender = get_object_or_404(User, id=user_id)
    receiver = get_object_or_404(User, username=username)

    if not (sender in receiver.followers.all() and receiver in sender.followers.all()):
        return render(request, "home/error.html", {
            "error": "You can only message users you both follow."
        })
    # Get or create conversation between sender and receiver
    conversation = Conversation.objects.filter(
        participants=sender
    ).filter(
        participants=receiver
    ).first()

    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(sender, receiver)

    # Send message (POST request)
    if request.method == "POST":
        text = request.POST.get("message")
        image = request.FILES.get("image")
        video = request.FILES.get("video")

        if text or image:
            Message.objects.create(
                conversation=conversation,
                sender=sender,
                message=text,
                image=image,
                video=video
            )

        return redirect('can_message', username=username)

    # Get all messages in this conversation
    messages = Message.objects.filter(
        conversation=conversation
    ).order_by('timestamp')

    # Mark messages as read (only receiver side)
    messages.filter(is_read=False).exclude(sender=sender).update(is_read=True)

    return render(request, "home/can_message.html", {
        "messages": messages,
        "receiver": receiver,
        "conversation": conversation
    })

def post(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)

    if request.method == "POST":
        title = request.POST.get("title")
        files = request.FILES.getlist("files")

        # Create post
        post = Post.objects.create(user=user, title=title)

        # Save files
        for file in files:
            if file.content_type.startswith("image"):
                PostImage.objects.create(post=post, image=file)

            elif file.content_type.startswith("video"):
                PostVideo.objects.create(post=post, video=file)

        return redirect('/home/')  # after posting

    return render(request, "home/post.html")
    

def post_detail(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    post = get_object_or_404(Post, id=post_id)
    return render(request, "home/post_detail.html", {"post": post})



def like_post(request,post_id) :
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    
    user = User.objects.get(id=user_id)
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        like, created = Like.objects.get_or_create(user=user, post=post)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        return JsonResponse({
            "liked": liked,
            "count": post.likes.count()
        })
        

def comment_post(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)
    post = get_object_or_404(Post, id=post_id)

    # handle comment submission
    if request.method == "POST":
        text = request.POST.get("comment")

        if text:
            Comment.objects.create(
                user=user,
                post=post,
                text=text
            )
            return redirect(request.path)

    comments = post.comments.all().order_by("-id")

    return render(request, "home/post_comment.html", {
        "post": post,
        "comments": comments,
        "user": user
    })


def edit_profile(request) :
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)
    if request.method == "POST":
        name = request.POST.get('name')
        username = request.POST.get('username')
        bio = request.POST.get('bio', '')
        bio = bio.replace('\r\n', '\n').replace('\r', '\n')
        bio = "\n".join(line.strip() for line in bio.split("\n") if line.strip())
        is_private = request.POST.get('is_private') == 'on'
        profile_image = request.FILES.get('profile_img',None)

        if User.objects.filter(username=username).exclude(id=user.id).exists():
            messages.warning(request, "Username already exists")
            return redirect(request.path)
        
        user.name = name
        user.username = username
        user.bio = bio
        user.is_private = is_private
        if profile_image :
            user.profile_image = profile_image
        user.save()
        return redirect("profile", username=user.username)
        
    return render(request, "home/edit_profile.html", {"user":user})


def is_discoverable(request) :

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    user = User.objects.get(id=user_id)
    if request.method == "POST":
        discoverable = request.POST.get('is_discoverable') == 'on'
        user.discoverable = discoverable
        user.save()
        return JsonResponse({
            'success': True,
            'discoverable': user.discoverable
        })

    return redirect("profile", username=user.username)

def find_friends(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')

    friends = []
    is_friend = False
    if request.method == "POST":
        min_age = int(request.POST.get("min_age"))
        max_age = int(request.POST.get("max_age"))
        gender = request.POST.get("gender")

        all_friends = User.objects.filter(discoverable=True).exclude(id=user_id)

        if gender != "all" and gender:
            all_friends = all_friends.filter(gender=gender)

        today = date.today()
        filtered_friends = []

        for f in all_friends:
            if f.dob:
                age = today.year - f.dob.year - ((today.month, today.day) < (f.dob.month, f.dob.day))
                if min_age <= age <= max_age:
                    filtered_friends.append(f)

        friends = filtered_friends
        is_friend = True

    # Render template
    return render(request, "home/find_friends.html", {"friends": friends, "is_friend" : is_friend})


def followers_list(request,username) :

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    
    user = User.objects.get(id=user_id)
    profile_user = get_object_or_404(User, username=username)


    if profile_user.is_private and user != profile_user and user not in profile_user.followers.all():
        return render(request, "home/error.html", {
            "error": "You cannot view followers of this private account."
        })

    profile_user_followers = profile_user.followers.all()

    return render(request,"home/followers-list.html", {'user': user,
    'profile_user': profile_user,
    'profile_user_followers': profile_user_followers,
    'title': "Followers"})



def following_list(request, username):

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    
    user = User.objects.get(id=user_id)
    profile_user = get_object_or_404(User, username=username)

    
    if profile_user.is_private and user != profile_user and user not in profile_user.followers.all():
        return render(request, "home/error.html", {
            "error": "You cannot view following of this private account."
        })

    profile_user_following = profile_user.following.all()

    return render(request, "home/following-list.html", {
        'user': user,
        'profile_user': profile_user,
        'profile_user_following': profile_user_following,
        'title': "Following"
    })



def remove_follower(request, username):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    
    user = User.objects.get(id=user_id)  
    follower = get_object_or_404(User, username=username)  

    if follower in user.followers.all():
        user.followers.remove(follower)
        follower.following.remove(user) 

    return redirect('followers_list', username=user.username)

def unfollow_user(request, username):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
    
    user = User.objects.get(id=user_id)  
    following_user = get_object_or_404(User, username=username)  

    if following_user in user.following.all():
        user.following.remove(following_user)
        following_user.followers.remove(user)  

    return redirect('following_list', username=user.username)


def delete_account(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/')
     
    if request.method == "POST":
        password = request.POST.get("password")
        user = get_object_or_404(User, id=user_id)

        if user.check_password(password):
            logout(request)
            user.delete()
            return redirect("/")
        else:
            messages.warning(request, "Incorrect password")

    return render(request, "home/delete.html")