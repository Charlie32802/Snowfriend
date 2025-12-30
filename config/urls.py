from django.contrib import admin
from django.urls import path
from accounts import views as account_views
from chatbot import views as chatbot_views
from feedback import views as feedback_views
from django.conf import settings
from django.conf.urls.static import static

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
    path('chat/api/clear-all/', chatbot_views.clear_conversation_and_memory, name='clear_conversation_and_memory'),
    path('chat/api/generate-title/', chatbot_views.generate_title, name='generate_title'),
    path('chat/api/export/', chatbot_views.export_conversation, name='export_conversation'),
    path('feedback/api/submit/', feedback_views.submit_feedback, name='submit_feedback'),
    path('chat/api/send/streaming/', chatbot_views.chat_api_send_streaming, name='chat_api_send_streaming'),
    path('chat/api/limit/', chatbot_views.get_message_limit, name='message_limit'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)