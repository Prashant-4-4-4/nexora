from django.contrib import admin
from .models import User, Conversation, Message, Post, PostImage, PostVideo, Like, Comment
admin.site.register(User)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register( Post)
admin.site.register(PostImage)
admin.site.register(PostVideo)
admin.site.register(Like)
admin.site.register(Comment)

