"""
URL configuration for humm_fondos project.
Orientador de Financiamiento Humm
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView

urlpatterns = [
    # Redirección automática de /admin/ hacia el panel de administración oficial de Humm (/gestion/)
    path('admin/', RedirectView.as_view(url='/gestion/', permanent=False)),
    # Django admin nativo disponible en /django-admin/ para operaciones de sistema de bajo nivel
    path('django-admin/', admin.site.urls),
    # Rutas de la plataforma Humm (público y /gestion/)
    path('', include('orientador.urls')),
    # Redirección amigable si se invoca desde el prefijo /herramientas/financiamiento/
    re_path(r'^herramientas/financiamiento/(?P<path>.*)$', RedirectView.as_view(url='/%(path)s', permanent=False)),
]
