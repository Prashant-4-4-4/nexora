from django.urls import path
from . import views


urlpatterns = [
    
    path('', views.home, name='home'),
    path('search', views.search, name='search' ),
    path('profile/<slug:username>/', views.profile, name='profile' ),
    path('request', views.request, name='request' ),
    path('logout', views.logout, name='logout' ),
    path('message/<slug:username>', views.can_message, name='can_message' ),
    path('messages', views.message_list, name='message_list' ),
    path('post/', views.post, name='post' ),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('comment/<int:post_id>/', views.comment_post, name='comment_post'),
    path('edit_profile/', views.edit_profile, name='edit_profile' ),
    path('is_discoverable/', views.is_discoverable, name='is_discoverable' ),
    path('find_friends/', views.find_friends, name='find_friends' ),
    path('followers/<str:username>/', views.followers_list, name='followers_list'),
    path('following/<str:username>/', views.following_list, name='following_list'),
    path('remove-follower/<str:username>/', views.remove_follower, name='remove_follower'),
    path('unfollow-user/<str:username>/', views.unfollow_user, name='unfollow_user'),
    path('delete-account/', views.delete_account, name='delete_account')

]
