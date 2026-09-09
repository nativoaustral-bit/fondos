"""
URL configuration for humm_fondos project.
Orientador de Financiamiento Humm
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Ruta canónica directa (para subdominios como fondos.humm.cl o ejecución independiente)
    path('', include('orientador.urls')),
    # Redirección amigable si se invoca desde el prefijo /herramientas/financiamiento/
    re_path(r'^herramientas/financiamiento/(?P<path>.*)$', RedirectView.as_view(url='/%(path)s', permanent=False)),
]
