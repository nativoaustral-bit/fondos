# 🚀 Humm Fondos (Humm Financiamiento)

> **Orientador de Financiamiento de Comunidad Humm** — Herramienta ágil, determinista y mobile-first para que emprendedores en Chile encuentren instrumentos no reembolsables pertinentes (subsidios, fondos concursables, premios y vouchers).

---

## 📋 Resumen del Proyecto

* **Propósito**: Orientar a emprendedores (ideas, prototipos, ventas informales y microempresas formalizadas) respondiendo hasta 5 preguntas clave para obtener recomendaciones claras, qué financian, para quiénes están diseñados, montos de referencia y qué condiciones confirmar antes de postular.
* **Cobertura Territorial**: Nacional (16 regiones de Chile), con especial atención inicial a Los Ríos, Los Lagos, Aysén y Magallanes.
* **Stack Tecnológico**:
  * **Backend**: Django 6.1 (Python 3.14+) con renderizado del lado del servidor (SSR) y motor determinista de compatibilidad y vigencia temporal.
  * **Base de Datos**: Soporte dual: **SQLite** por defecto (`db.sqlite3` con timeout de 20s, respaldos en 1 archivo) y **MySQL / MariaDB** (HostGator cPanel) configurable vía `.env`.
  * **Frontend**: HTML5 Semántico, Vanilla CSS estructurado con tokens Humm (#F7F8F4, #203B36, #245C50, #E4EEE7, #FFF1D5) y JavaScript nativo liviano (cero frameworks pesados). Cumple WCAG 2.2 AA (objetivos táctiles 44×44px, foco visible, contraste > 4.5:1).
  * **Contrato de Datos**: Microsoft Excel (.xlsx) estructurado en 5 hojas (`Control`, `Entidades`, `Instrumentos`, `Convocatorias`, `Diccionario`) con previsualización de diferencias (*diffs*), validación de esquemas y transacciones atómicas.

---

## 🛠️ Instalación y Puesta en Marcha Local

### 1. Clonar o ingresar al directorio del proyecto

```bash
cd /Users/rmerinog/PLATAFORMAS/FONDOS
```

### 2. Crear y activar entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

*(O manualmente: `pip install django openpyxl pytest pytest-django`)*

### 4. Ejecutar migraciones de base de datos

```bash
python manage.py migrate
```

### 5. Inicializar cuestionario oficial de 5 preguntas

```bash
python manage.py setup_initial_data
```

### 6. Cargar la base de fondos inicial

El proyecto incluye el conversor oficial que normaliza el inventario `Base_fondos_no_reembolsables_Chile_MVP-2.xlsx`:

```bash
# Cargar en borrador (recomendado para revisión editorial):
python manage.py convert_legacy_base

# O cargar directamente publicados para pruebas inmediatas:
python manage.py convert_legacy_base --publicar
```

### 7. Crear el primer usuario administrador (sin contraseñas por defecto)

```bash
python manage.py create_admin
```
*(Solicitará de forma segura nombre de usuario, correo y contraseña sin dejar credenciales grabadas en código).*

### 8. Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

Abre en tu navegador:
* **Orientador Público**: [http://localhost:8000/](http://localhost:8000/) o [http://localhost:8000/herramientas/financiamiento/](http://localhost:8000/herramientas/financiamiento/)
* **Panel de Gestión Humm**: [http://localhost:8000/gestion/](http://localhost:8000/gestion/)
* **Admin Django**: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## ⚙️ Variables de Entorno (Configuración)

Puedes crear un archivo `.env` o definir las siguientes variables en el servidor:

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `DEBUG` | Modo depuración (`True`/`False`) | `True` en local, `False` en prod |
| `SECRET_KEY` | Clave criptográfica única de Django | Clave segura aleatoria |
| `ALLOWED_HOSTS` | Dominios permitidos separados por coma | `localhost,127.0.0.1,.humm.cl` |
| `DB_ENGINE` | Motor de base de datos (`sqlite3` o `mysql`) | `sqlite3` |
| `DB_NAME` | Nombre de la base de datos MySQL (en cPanel) | `humm_fondos` |
| `DB_USER` | Usuario de base de datos MySQL | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `""` |
| `DB_HOST` | Host de base de datos | `localhost` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes confiables CSRF | `https://*.humm.cl` |

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas unitarias y de integración que validan los comportamientos críticos del motor:

```bash
source .venv/bin/activate
pytest -v
```

Casos verificados:
1. **Reglas temporales y de vigencia (Sección 10)**: cierre vencido automático ("Plazo informado finalizado"), cierre hoy sin hora ("Cierra hoy: confirmar hora"), apertura prevista sin comprobación, suspensión prevalente sobre calendario, y desactualización de instrumentos (>90 días).
2. **Motor de orientación determinista (Sección 8 y 9)**: filtro territorial por región, negocio informal clasificado en "Para una próxima etapa", selección múltiple de necesidades, conservación de base de cálculo de aporte propio (3% del subsidio vs costo total), y monto no excluyente.
3. **Contrato Excel .xlsx (Sección 12 y 13)**: exportación/reimportación idéntica, aplicación de `HEREDAR`, `__BORRAR__` y celdas vacías, rechazo atómico ante datos corruptos, detección de colisiones de versión, y reversión de lotes.
4. **Flujo público y seguridad (Sección 16 y 17)**: cuestionario de 5 preguntas, protección anti doble clic en solicitudes de apoyo (idempotencia) y bloqueo de rutas administrativas no autorizadas.

---

## 🚀 Despliegue en HostGator (Patrón Probado en ReLoop)

El proyecto incluye los archivos preconfigurados para HostGator sin necesidad de `PythonApp` en cPanel:

1. **`passenger_wsgi.py`**: Puente WSGI/CGI compatible con el entorno de servidor compartido.
2. **`.htaccess`**: Reglas de Apache con `AddHandler cgi-script .py .cgi` y entrega directa de archivos `/static/` y `/media/`.
3. **`deploy.sh`**: Script de sincronización vía `rsync` y SSH.

### Pasos de Despliegue:

1. Asegúrate de tener acceso SSH configurado al servidor `humm.cl`.
2. Ejecuta el script de despliegue:
   ```bash
   ./deploy.sh
   ```
3. El script sincroniza los archivos, ejecuta migraciones, compila los archivos estáticos (`collectstatic`) y reinicia el servicio.

---

## 📂 Documentación Complementaria

* [MANUAL_ADMINISTRADOR.md](file:///Users/rmerinog/PLATAFORMAS/FONDOS/MANUAL_ADMINISTRADOR.md): Guía de uso de las 4 secciones administrativas, gestión de preguntas y ciclo de actualización Excel.
* [INSTRUCCIONES_ACTUALIZACION_CATALOGO.md](file:///Users/rmerinog/PLATAFORMAS/FONDOS/INSTRUCCIONES_ACTUALIZACION_CATALOGO.md): Pauta y protocolo para el chat de investigación oficial.
* [DICCIONARIO_DATOS.md](file:///Users/rmerinog/PLATAFORMAS/FONDOS/DICCIONARIO_DATOS.md): Descripción de tablas, columnas, códigos válidos y convenciones del contrato `.xlsx`.
* [INFORME_MIGRACION_INICIAL.md](file:///Users/rmerinog/PLATAFORMAS/FONDOS/INFORME_MIGRACION_INICIAL.md): Registro de normalización de la base legacy a la estructura canónica.
