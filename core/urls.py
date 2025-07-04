from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from users.views import login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('helpdesk/', include('helpdesk.urls')),
    path('users/', include('users.urls')),
    path('', login_view),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)