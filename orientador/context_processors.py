from .models import ConfiguracionGlobal


def humm_global_context(request):
    """
    Inyecta la configuración global de Humm (nombre, URL de retorno, etc.)
    en todos los templates de forma eficiente.
    """
    try:
        config = ConfiguracionGlobal.get_solo()
    except Exception:
        config = None

    return {
        'humm_config': config,
    }
