from django.contrib import admin
from django.urls import path
from accounts import views as account_views
from chatbot import views as chatbot_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Account routes
    path('', account_views.landing_page, name='landing'),
    path('login/', account_views.login_page, name='login'),
    path('register/', account_views.register_page, name='register'),
    path('dashboard/', account_views.dashboard, name='dashboard'),
    path('logout/', account_views.logout_view, name='logout'),
    
    # Chat page
    path('chat/', account_views.chat_page, name='chat'),
    
    # Chatbot API endpoints
    path('chat/api/send/', chatbot_views.send_message, name='send_message'),
    path('chat/api/history/', chatbot_views.get_conversation_history, name='get_history'),
    path('chat/api/clear/', chatbot_views.clear_conversation, name='clear_conversation'),
    path('chat/api/generate-title/', chatbot_views.generate_title, name='generate_title'),
    path('chat/api/export/', chatbot_views.export_conversation, name='export_conversation'),
]