# INFORME HUMM RELEASE GATE v2
### Auditoría Técnica Independiente, Seguridad, Integridad y Preparación Operacional
**Protocolo:** HUMM RELEASE GATE v2 + ADDENDUM v2.1  
**Fecha de Evaluación:** 10 de septiembre de 2026  
**Auditor:** Equipo Auditor Técnico Independiente y Adversarial  

---

## 1. Identificación de la Aplicación y Entorno

| Parámetro | Detalle |
|---|---|
| **Aplicación** | **Humm Fondos (Humm Financiamiento)** |
| **Repositorio** | `nativoaustral-bit/fondos` |
| **Finalidad** | Orientador determinista mobile-first para que emprendedores en Chile encuentren instrumentos de financiamiento público y privado no reembolsables (subsidios, fondos concursables, premios y vouchers). |
| **Framework & Versiones** | Django 6.1.1 / Python 3.14+ |
| **Arquitectura** | Monolito SSR (Server-Side Rendering) con Vanilla CSS, HTML5 Semántico y JavaScript nativo liviano (cero frameworks pesados). |
| **Base de Datos** | SQLite 3 (`db.sqlite3` con timeout de 20s en HostGator) con soporte de configuración para MySQL / MariaDB. |
| **Infraestructura de Producción** | Servidor Compartido HostGator (cPanel), Apache con módulo CGI / Passenger (`passenger_wsgi.py`). |
| **URLs Operativas** | Pública: `https://fondos.humm.cl/` · Gestión Humm: `https://fondos.humm.cl/gestion/` |
| **Entornos Evaluados** | **LOCAL** (código fuente, suite pytest de 33 pruebas, check Django) y **SERVIDOR REAL** (`fondos.humm.cl` y `humm.cl/FONDOS/` en HostGator). |

---

## 2. Clasificación de Etapa y Perfil de Complejidad

### Etapa del Producto
Conforme a la regla de clasificación por defecto (Sección 3):
# ETAPA A — MVP / PILOTO CONTROLADO
* **Objetivo:** Validar la utilidad de la orientación determinista, la experiencia de usuario y la tasa de conversión en solicitudes voluntarias de apoyo con los primeros emprendedores bajo supervisión directa de Comunidad Humm.
* **Criterio de Auditoría:** *¿Puede utilizarse responsablemente con los primeros usuarios reales bajo supervisión directa de Humm sin exponer a la organización ni a los usuarios a fuga de datos, pérdida de información o vulnerabilidades críticas?*

### Perfil de Complejidad de la Aplicación

| Dimensión | Nivel | Justificación Técnica |
|---|:---:|---|
| **Usuarios autenticados** | **BAJA** | Únicamente administradores de Comunidad Humm acceden al panel `/gestion/` y `/django-admin/`. Los emprendedores consultan de forma anónima. |
| **Múltiples roles** | **BAJA** | No existen roles intermedios ni jerarquías complejas; únicamente rol de Administrador (`is_staff` / `is_superuser`). |
| **Multitenancy / Empresas** | **NO APLICA** | Plataforma monotenant operada en exclusiva por Comunidad Humm para orientación a emprendedores individuales. |
| **Clientes finales** | **BAJA** | Emprendedores consultando fondos de forma libre; interacción reducida a cuestionario y modal voluntario de apoyo. |
| **Pagos / Transacciones** | **NO APLICA** | No procesa pagos, carritos, transferencias ni cobros. Los instrumentos orientan hacia subsidios gubernamentales (Sercotec, Corfo, etc.). |
| **Información Bancaria** | **NO APLICA** | No se recopila ningún dato financiero, cuenta bancaria ni tarjeta. |
| **Datos Personales (PII)** | **MEDIA** | Nombres, canales de contacto (teléfono/WhatsApp, correo) y mensajes libres almacenados en la tabla `SolicitudApoyo`. |
| **Archivos / Uploads** | **MEDIA** | Carga de planillas Excel `.xlsx` restringida exclusivamente a administradores para actualización masiva del catálogo. |
| **Servicios Externos / APIs** | **NO APLICA** | El motor de búsqueda y vigencia opera de forma determinista 100% autónomo y local; no hay llamadas síncronas a APIs de terceros. |
| **Correo Saliente** | **BAJA** | Configurado en `django.core.mail.backends.console.EmailBackend`. No realiza envíos SMTP activos. |
| **Concurrencia / Base de Datos** | **BAJA** | Catálogo estructurado de 71 instrumentos y 35 convocatorias; lecturas optimizadas y escrituras esporádicas. |

---

## 3. VEREDICTO HUMM RELEASE GATE v2

# 🔴 NO APTO PARA PILOTO
*(BLOQUEADO POR 5 HALLAZGOS P0 EN INFRAESTRUCTURA Y SERVIDOR REAL)*

> **Justificación del Veredicto:**  
> Aunque la lógica de negocio, el motor determinista de compatibilidad territorial y la suite de pruebas unitarias locales (33/33 aprobadas) demuestran una arquitectura limpia, modular y bien probada, **el despliegue en la infraestructura real de HostGator presenta fallas críticas de seguridad perimetral y preservación de datos**.  
> Específicamente: la base de datos productiva SQLite completa y el repositorio `.git/` son descargables directamente desde internet por cualquier visitante anónimo; el modo `DEBUG=True` se encuentra activo en producción; la `SECRET_KEY` productiva es una clave insegura pública por defecto; y el script de despliegue `deploy.sh` sobreescribirá y destruirá los datos del servidor real al ejecutarse.  
> **El piloto NO puede iniciarse hasta remediar de inmediato los 5 bloqueadores P0.**

---

## 4. Resumen Ejecutivo de Hallazgos

```
┌─────────────────────────────────────────────────────────────┐
│  P0 (Bloqueantes Críticos)       : 5                        │
│  P1 (Corregir Preferentemente)   : 5                        │
│  DT (Deuda Técnica Aceptada)     : 7                        │
│  ESC (Requerimientos Escalamiento): 4                        │
│  Pruebas Automatizadas Locales   : 33 Pasadas / 0 Fallidas  │
└─────────────────────────────────────────────────────────────┘
```

* **Riesgo de Pérdida de Datos:** **CRÍTICO**. La base de datos `db.sqlite3` está versionada en Git y `deploy.sh` ejecuta un `git reset --hard origin/main` en el servidor, lo que borrará las solicitudes y cambios reales. Además, no existe ningún mecanismo ni script de respaldo (Backup Inexistente).
* **Fuga de Información y Exposición:** **CRÍTICO**. El directorio de trabajo `/home1/paulocis/public_html/FONDOS` está expuesto bajo el dominio web principal `humm.cl`. La base de datos con contraseñas hash y datos de contacto (`db.sqlite3`), el repositorio completo (`.git/`) y los scripts del servidor (`deploy.sh`) son accesibles públicamente vía HTTP.
* **Configuración Web en Servidor:** **DEFICIENTE**. `DEBUG = True` en el servidor real expone trazas completas; las cookies de sesión y CSRF carecen del flag `Secure`; y la `SECRET_KEY` es la clave insegura por defecto de Django.
* **Aislamiento y Autenticación:** **APROBADO EN CÓDIGO**. Todas las vistas administrativas en `/gestion/` validan `es_administrador` en el backend y requieren CSRF. No hay multitenancy ni roles cruzados.

---

## 5. Respuestas a las 5 Preguntas Finales de la Regla v2.1

| Pregunta Obligatoria | Respuesta | Evidencia Técnica |
|---|:---:|---|
| **1. ¿Puede alguien sin sesión leer o modificar información?** | **SÍ (LECTURA TOTAL)** | Cualquier usuario en internet puede descargar directamente el archivo `https://humm.cl/FONDOS/db.sqlite3` conteniendo toda la base de datos (usuarios, contraseñas PBKDF2, solicitudes de contacto con PII, auditorías y sesiones). |
| **2. ¿Puede un usuario manipular parámetros del navegador para transformarse en otro usuario, rol o tenant?** | **NO** | No existe multitenancy ni parámetros en cliente para alterar privilegios. La autorización de administración se valida exclusivamente en backend mediante sesiones firmadas por Django (`request.user.is_staff`). |
| **3. ¿Existe alguna contraseña, endpoint o mecanismo alternativo que evite la autenticación normal?** | **NO** | No existen contraseñas maestras ni cuentas de demostración activas. El comando `create_admin` no contiene claves cableadas. Todas las rutas de modificación exigen sesión staff. |
| **4. ¿Algún secreto productivo estuvo expuesto y todavía continúa siendo válido?** | **SÍ** | La `SECRET_KEY` en `settings.py` (`django-insecure-[REDACTED]`) es la que opera activamente en producción. Asimismo, `deploy.sh` expone el usuario SSH, puerto y rutas absolutas del servidor real. |
| **5. ¿Los propios archivos o informes de auditoría contienen información que no debería conservarse o compartirse?** | **NO** | Los documentos de especificación del repositorio no contienen secretos sin redactar. En este informe todos los secretos sensibles han sido debidamente enmascarados bajo la regla de redacción obligatoria. |

---

## 6. Inventario Detallado de Hallazgos

### Hallazgos P0 — Bloqueadores Inmediatos

#### [P0-1] Exposición y Descarga Pública de la Base de Datos Productiva (`db.sqlite3`)
* **Componente:** Servidor Web Apache / Despliegue en cPanel (`public_html/FONDOS/db.sqlite3`)
* **Severidad:** **P0 — BLOQUEADOR** (CWE-538 / OWASP A01 & A05)
* **Entorno de Evidencia:** **SERVIDOR REAL**
* **Descripción:** La aplicación fue desplegada en el directorio `/home1/paulocis/public_html/FONDOS`, el cual forma parte de la raíz web pública del dominio `humm.cl`. El archivo `.htaccess` contiene una regla que sirve directamente cualquier archivo existente en disco (`RewriteCond %{REQUEST_FILENAME} -f -> RewriteRule ^ - [L]`), sin excluir archivos `.sqlite3` ni archivos de base de datos.
* **Prueba Realizada:** Solicitud HTTP GET no destructiva:
  ```bash
  curl -sI https://humm.cl/FONDOS/db.sqlite3
  ```
* **Resultado Obtenido:**
  ```http
  HTTP/2 200
  last-modified: Fri, 11 Sep 2026 00:41:21 GMT
  accept-ranges: bytes
  content-length: 385024
  server: Apache
  ```
* **Impacto:** Fuga total de la base de datos en producción. Cualquier atacante o bot puede descargar la base completa conteniendo:
  1. Tabla `auth_user` con los nombres de usuario y hashes criptográficos de contraseñas de los administradores.
  2. Tabla `django_session` con identificadores de sesión.
  3. Tabla `orientador_solicitudapoyo` con nombres, números de teléfono/WhatsApp, correos electrónicos y consultas de emprendedores.
* **Recomendación de Remediación:** Mover el directorio de la aplicación fuera de `public_html` (ej. `/home1/paulocis/apps/FONDOS`) o agregar una regla estricta e inmediata en `.htaccess` (`<FilesMatch "\.(sqlite3|env|git|sh|py)$"> Deny from all </FilesMatch>`) que prohíba de raíz el acceso web a estos archivos.

---

#### [P0-2] Exposición Pública del Repositorio Git Completo (`.git/`) y Script de Despliegue (`deploy.sh`)
* **Componente:** Servidor Web Apache / Control de Versiones (`public_html/FONDOS/.git/`)
* **Severidad:** **P0 — BLOQUEADOR** (CWE-538 / OWASP A05)
* **Entorno de Evidencia:** **SERVIDOR REAL**
* **Descripción:** Debido a la misma exposición del directorio `public_html/FONDOS`, la carpeta oculta `.git/` y los scripts operativos son servidos como archivos estáticos públicos.
* **Prueba Realizada:**
  ```bash
  curl -s https://humm.cl/FONDOS/.git/config
  curl -sI https://humm.cl/FONDOS/.git/logs/HEAD
  curl -s https://humm.cl/FONDOS/deploy.sh
  ```
* **Resultado Obtenido:**
  * `.git/config` devuelve `HTTP/2 200` con la configuración del repositorio GitHub (`nativoaustral-bit/fondos.git`).
  * `.git/logs/HEAD` devuelve `HTTP/2 200` (682 bytes).
  * `deploy.sh` devuelve `HTTP/2 200` exponiendo el usuario SSH del servidor, puerto no estándar, host y rutas internas.
* **Impacto:** Permite a herramientas automatizadas reconstruir el 100% del código fuente, el historial de cambios y acceder a la arquitectura interna del servidor en HostGator.
* **Recomendación de Remediación:** Denegar acceso a toda la carpeta `.git` y scripts `.sh` en Apache, o trasladar el proyecto fuera del árbol web público.

---

#### [P0-3] Script de Despliegue Destructivo Capaz de Sobreescribir la Base de Datos Productiva
* **Componente:** `deploy.sh` y `.gitignore`
* **Severidad:** **P0 — BLOQUEADOR** (Sección 16 HUMM: *Un deployment capaz de destruir la base es P0*)
* **Entorno de Evidencia:** **LOCAL y SERVIDOR REAL**
* **Descripción:** 
  1. El archivo `db.sqlite3` fue incluido en el commit inicial `fc6ee03` y se encuentra activamente rastreado en Git (`git ls-files db.sqlite3` devuelve `db.sqlite3`).
  2. En `.gitignore`, únicamente se ignora `db.sqlite3-journal`, pero NO `db.sqlite3`.
  3. En `deploy.sh` (línea 18), el despliegue manual ejecuta en el servidor:
     ```bash
     cd ${REMOTE_DIR} && git fetch origin main && git reset --hard origin/main ...
     ```
* **Impacto:** Cada vez que un desarrollador ejecute `./deploy.sh`, la base de datos viva en el servidor de producción será forzosamente reemplazada (`git reset --hard`) por la versión que esté en el repositorio, destruyendo de forma irreversible todas las solicitudes de apoyo enviadas por emprendedores reales, las nuevas cuentas de administración y las modificaciones de catálogo realizadas en producción.
* **Recomendación de Remediación:** Eliminar `db.sqlite3` del control de versiones (`git rm --cached db.sqlite3`), agregar `db.sqlite3` a `.gitignore`, y asegurar que los scripts de despliegue verifiquen la no sobreescritura de datos.

---

#### [P0-4] Modo Depuración Activo en Producción (`DEBUG = True`)
* **Componente:** `humm_fondos/settings.py` / Entorno HostGator
* **Severidad:** **P0 — BLOQUEADOR** (OWASP A05 / ASVS V14 / Django `security.W018`)
* **Entorno de Evidencia:** **SERVIDOR REAL**
* **Descripción:** En `settings.py`:
  ```python
  DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
  ```
  En HostGator (entorno cPanel con Apache Passenger/CGI), las variables de entorno de shell no se transfieren al proceso WSGI y el código no incluye ningún módulo de carga de archivo `.env` (como `python-dotenv`). En consecuencia, el servidor productivo opera con el valor predeterminado `DEBUG = True`.
* **Prueba Realizada:** Solicitud a una ruta inexistente en el dominio público:
  ```bash
  curl -s https://fondos.humm.cl/ruta-inexistente-debug-test-12345/
  ```
* **Resultado Obtenido:**
  Responde con la página técnica oficial de depuración de Django:
  ```html
  <title>Page not found at /ruta-inexistente-debug-test-12345/</title>
  ...
  <header id="summary">
    <h1>Page not found <small>(404)</small></h1>
  ...
  ```
  Exponiendo todas las rutas internas registradas (`ROOT_URLCONF`).
* **Impacto:** Ante cualquier error inesperado 500 o 404, Django renderiza información sensible del servidor: variables de entorno, nombres de tablas, estructura de base de datos, rutas físicas del servidor y fragmentos de código.
* **Recomendación de Remediación:** Cargar formalmente variables de entorno en `settings.py` (o mediante `.htaccess` `SetEnv`) y forzar `DEBUG = False` en producción, configurando plantillas amigables `404.html` y `500.html`.

---

#### [P0-5] Clave Criptográfica `SECRET_KEY` Insegura por Defecto en Producción
* **Componente:** `humm_fondos/settings.py`
* **Severidad:** **P0 — BLOQUEADOR** (OWASP A02 / Django `security.W009`)
* **Entorno de Evidencia:** **LOCAL y SERVIDOR REAL**
* **Descripción:** En `settings.py`:
  ```python
  SECRET_KEY = os.environ.get(
      'SECRET_KEY',
      'django-insecure-[REDACTED]'
  )
  ```
  Al no inyectarse variables de entorno en el servidor compartido, la aplicación productiva en `fondos.humm.cl` está firmando todas sus operaciones criptográficas con una clave pública, hardcodeada y prefijada con `django-insecure-`.
* **Impacto:** Un atacante con conocimiento de la `SECRET_KEY` puede manipular firmas criptográficas de Django, comprometiendo la integridad de tokens y sesiones.
* **Recomendación de Remediación:** Generar una clave criptográfica de al menos 50 caracteres aleatorios y cargarla de forma segura y obligatoria desde el entorno, sin permitir arranque si la clave no está definida o es insegura.

---

### Hallazgos P1 — Corregir Preferentemente

#### [P1-1] Ausencia Total de Automatización y Procedimiento de Respaldo (Backup Inexistente)
* **Componente:** Operación / Infraestructura
* **Severidad:** **P1** (Sección 14 HUMM: *Diferencia Backup Inexistente de Backup Probado*)
* **Entorno de Evidencia:** **LOCAL y SERVIDOR REAL**
* **Descripción:** El repositorio carece de scripts, tareas programadas (cron) o comandos de gestión para generar copias de seguridad de `db.sqlite3`.
* **Impacto:** Si la base se corrompe por escrituras concurrentes o es eliminada por un fallo del hosting, no existe punto de restauración (RTO y RPO indefinidos).
* **Recomendación:** Implementar un comando de respaldo automático programado vía cPanel Cron y exportado fuera del servidor local.

---

#### [P1-2] Redirección Abierta (Open Redirect) en Endpoint de Login Administrativo
* **Componente:** `orientador/views/admin_views.py` (`admin_login_view`)
* **Severidad:** **P1** (CWE-601 / OWASP A01)
* **Entorno de Evidencia:** **LOCAL**
* **Descripción:** En las líneas 34 y 45:
  ```python
  next_url = request.GET.get('next') or request.POST.get('next') or '/gestion/'
  ...
  return redirect(next_url)
  ```
  No se realiza ninguna validación sobre si `next_url` apunta al mismo dominio o a un sitio externo antes de emitir la redirección HTTP.
* **Impacto:** Permite a un atacante construir enlaces de phishing convincentes dirigidos a los administradores de Humm (ej. `https://fondos.humm.cl/gestion/login/?next=https://sitio-malicioso.com`).
* **Recomendación:** Utilizar la función oficial `django.utils.http.url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})` antes de redirigir.

---

#### [P1-3] Potencial Vector XSS por Asignación Directa a `innerHTML` en Modal de Apoyo
* **Componente:** `orientador/static/js/orientador.js` (líneas 165 y 176) y `public.py` (línea 175)
* **Severidad:** **P1** (CWE-79 / OWASP A03)
* **Entorno de Evidencia:** **LOCAL**
* **Descripción:** En la vista pública:
  ```python
  mensaje = f'Gracias {nombre}, hemos recibido tu solicitud...'
  ```
  Y en el cliente JavaScript:
  ```javascript
  feedbackEl.innerHTML = `<strong>¡Solicitud recibida con éxito!</strong><br>${data.mensaje}`;
  ```
  Si el campo `nombre` contiene etiquetas HTML o scripts (ej. `<img src=x onerror=...`), estas se interpretan directamente en el DOM del usuario.
* **Impacto:** Ejecución de código arbitrario en el navegador del usuario que envía la solicitud.
* **Recomendación:** Escapar el nombre antes de responder en JSON o utilizar `textContent` en lugar de `innerHTML` para inyectar datos dinámicos provenientes del usuario.

---

#### [P1-4] Cookies de Sesión y CSRF sin Flag `Secure` en HTTPS
* **Componente:** `humm_fondos/settings.py` / Servidor Real
* **Severidad:** **P1** (Django `security.W012` y `security.W016`)
* **Entorno de Evidencia:** **SERVIDOR REAL**
* **Descripción:** Las cabeceras HTTP de respuesta en `https://fondos.humm.cl/` emiten:
  `Set-Cookie: csrftoken=...; SameSite=Lax`
  `Set-Cookie: sessionid=...; HttpOnly; SameSite=Lax`
  Ninguna de las dos cookies incluye el flag `; Secure`.
* **Impacto:** Las cookies pueden ser transmitidas en texto claro ante solicitudes involuntarias sobre HTTP o inspección en redes no seguras.
* **Recomendación:** Establecer en `settings.py`:
  ```python
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  ```

---

#### [P1-5] Ausencia de Validación de Longitud en Campos de Solicitud de Apoyo
* **Componente:** `orientador/views/public.py` (`solicitar_apoyo_view`)
* **Severidad:** **P1** (Integridad / Robustez de Entradas)
* **Entorno de Evidencia:** **LOCAL**
* **Descripción:** La vista verifica que `nombre` y `contacto_valor` existan, pero no valida su longitud antes de persistir en base de datos.
* **Impacto:** Si la aplicación se conecta a MySQL (con `STRICT_TRANS_TABLES`), una entrada con más de 150 caracteres provocará un error de base de datos no controlado (`DataError`) y un fallo 500 para el usuario.
* **Recomendación:** Truncar o validar explícitamente `len(nombre) <= 150` y `len(contacto_valor) <= 150` en la capa de vista antes de invocar `SolicitudApoyo.objects.create()`.

---

### Deuda Técnica Aceptada (DT)
*Conforme a la filosofía Humm (Sección 1 y 29), estas limitaciones NO constituyen bloqueadores para el MVP bajo supervisión directa:*

1. **[DT-1] Motor de Base de Datos SQLite en Producción:** Aceptable para el volumen inicial de consultas del piloto (71 instrumentos y bajo volumen de escrituras). Se verifica `timeout: 20` para mitigar bloqueos temporales.
2. **[DT-2] Hosting Compartido Apache (HostGator):** Suficiente para validar utilidad en fase piloto sin necesidad de incurrir en costos de VPS o Cloud dedicados.
3. **[DT-3] Envío de Correos en Modo Consola (`console.EmailBackend`):** No existe pasarela SMTP saliente activa. En la etapa de piloto, las solicitudes de apoyo son revisadas manualmente por el orientador de Comunidad Humm directamente en el panel administrativo.
4. **[DT-4] Ausencia de Pasarela de Pagos:** Coherente con el modelo actual de orientación a instrumentos y subsidios de terceros. No hay cobros ni transacciones monetarias.
5. **[DT-5] Ausencia de Colas Asíncronas (Celery / Redis):** Las consultas deterministas y la importación de Excel se ejecutan sincrónicamente en milisegundos sin degradar el servidor.
6. **[DT-6] Monitoreo Básico sin APM Dedicado (Sentry / Datadog):** Para un MVP controlado con pocos usuarios conocidos y supervisión directa, la inspección periódica de logs y el semáforo del dashboard interno son suficientes.
7. **[DT-7] Recuperación de Contraseñas Administrativa:** No existe autoservicio de recuperación de contraseña; la restitución de accesos es supervisada directamente por Humm mediante consola (`python manage.py create_admin` o Django Admin).

---

### Requerimientos de Escalamiento (ESC)
*Mejoras no requeridas hoy, pero obligatorias ante aumento significativo de uso o comercialización:*

1. **[ESC-1] Migración a PostgreSQL o MySQL Dedicado:** Activar cuando se evidencien errores de concurrencia `database is locked` o cuando el volumen de solicitudes supere las 500 transacciones diarias.
2. **[ESC-2] Servidor Dedicado / VPS con Nginx y Gunicorn:** Reemplazar Apache CGI / Passenger cuando la concurrencia simultánea supere los límites del hosting compartido.
3. **[ESC-3] Proveedor de Correo Transaccional (SendGrid / Amazon SES / Resend):** Integrar cuando el volumen de solicitudes requiera confirmación inmediata automatizada al emprendedor y notificación al equipo.
4. **[ESC-4] Plataforma Centralizada de Monitoreo de Errores (Sentry):** Implementar cuando la aplicación opere sin supervisión directa continua del equipo de desarrollo.

---

## 7. Matriz de Controles Humm v2

| Dimensión de Control | Estado | Observación de Auditoría |
|---|:---:|---|
| **Arquitectura General** | **APROBADO** | Monolito SSR limpio, modular, desacoplado y sin sobreingeniería innecesaria. |
| **Autenticación en Backend** | **APROBADO** | Login server-side con hashing estándar de Django (PBKDF2 SHA256). Sin bypasses ni credenciales por defecto. |
| **Autorización y Rutas de Gestión** | **APROBADO** | Todas las vistas en `/gestion/` validan `es_administrador` en servidor y rechazan peticiones anónimas (302 a login). |
| **Aislamiento Multitenant** | **NO APLICA** | Plataforma monotenant para Comunidad Humm. |
| **Roles e Identidad** | **APROBADO** | Únicamente rol staff/superusuario. No hay roles intermedios con privilegios ambiguos. |
| **Integridad de Datos** | **APROBADO** | Importaciones Excel transaccionales (`transaction.atomic`), registro de auditoría campo por campo y clave de idempotencia anti doble clic en solicitudes. |
| **Base de Datos y Concurrencia** | **DEUDA TÉCNICA ACEPTADA** | SQLite con timeout de 20s. Aceptable para MVP de bajo volumen supervisado. |
| **Respaldo (Backups)** | **FALLA (P1)** | No existe script, cron ni automatización de respaldo. |
| **Restauración (Restore)** | **NO VERIFICADO** | Al no existir backups generados, no es posible comprobar el procedimiento de restauración. |
| **Deployment y Seguridad CI/CD** | **FALLA (P0)** | `db.sqlite3` bajo control de versiones y `deploy.sh` con `git reset --hard` capaz de destruir la base viva en el servidor. |
| **Migraciones de Base de Datos** | **APROBADO** | Esquema inicial limpio y ordenado (`0001_initial.py`). |
| **Seguridad de Entradas (SQLi)** | **APROBADO** | 100% de consultas vía ORM de Django con sentencias parametrizadas. Cero SQL en bruto. |
| **Cross-Site Scripting (XSS)** | **FALLA (P1)** | Templates limpios (cero `|safe` ni `mark_safe`), pero manipulación de `innerHTML` en JavaScript para mensajes de respuesta. |
| **Protección CSRF** | **APROBADO** | Middleware activo y token presente en todos los formularios públicos y administrativos. |
| **Seguridad de Archivos** | **APROBADO** | Carga de Excel restringida a administradores, validada por extensión y esquema de 5 hojas, con límite de 10 MB. |
| **Protección de Secretos** | **FALLA (P0)** | `SECRET_KEY` insegura activa en producción; `deploy.sh` expuesto públicamente. |
| **Seguridad Web (DEBUG / Headers)** | **FALLA (P0)** | `DEBUG = True` en el servidor real; cookies de sesión sin flag `Secure`. |
| **Pagos y Transacciones** | **NO APLICA** | No hay pasarela ni cobros. |
| **Privacidad y PII** | **FALLA (P0)** | Nombres y contactos de emprendedores en `SolicitudApoyo` expuestos por descarga directa de `db.sqlite3`. |
| **Dependencias y Versiones** | **APROBADO** | Pila mínima y moderna (Django 6.1.1, openpyxl 3.1.5, pytest 9.1.1). Sin paquetes obsoletos. |
| **Monitoreo y Alertas** | **DEUDA TÉCNICA ACEPTADA** | Dashboard interno con conteos y semáforos de vigencia. Suficiente para piloto supervisado. |
| **Pruebas Automatizadas** | **APROBADO** | 33 pruebas unitarias y de integración pasando con éxito en 1.91s. |
| **Frontera de Confianza Front/Back** | **APROBADO** | Los cálculos de pertinencia y vigencia se realizan íntegramente en backend en `matching_engine.py`. |

---

## 8. Humm Pilot Envelope (Condiciones Operacionales para el Piloto)

Una vez corregidos los bloqueadores P0, la aplicación podrá operar de forma segura bajo el siguiente marco:

* **Usuarios Concurrentes:** Hasta 10 consultas simultáneas en el orientador público.
* **Solicitudes de Apoyo:** Diseñado para recibir y almacenar ordenadamente hasta 100 solicitudes semanales con revisión diaria del equipo Humm.
* **Supervisión Operacional:** Monitoreo humano directo por parte de Comunidad Humm. Revisión manual semanal de convocatorias marcadas en estado *"Vigencia por confirmar"*.
* **Administración de Catálogo:** Actualizaciones masivas mediante el ciclo Excel de 5 pasos con previsualización obligatoria de diferencias (*Diff*).
* **Copias de Seguridad Requeridas:** Respaldo diario de `db.sqlite3` descargado fuera del servidor antes de aplicar nuevas versiones.

### Disparadores de Escalamiento (Kill-Switches de Arquitectura)
Se deberá detener el crecimiento y migrar a infraestructura superior si ocurre cualquiera de los siguientes eventos:
1. Errores recurrentes de `sqlite3.OperationalError: database is locked`.
2. Más de dos errores 500 registrados en un período de 24 horas.
3. Superación de 500 solicitudes de apoyo registradas al mes cuya gestión manual ya no sea viable.
4. Necesidad de integrar pagos directos o cobro por servicios dentro de la plataforma.

---

## 9. Candidatos a Limpieza Post-Remediación

Durante esta auditoría **no se eliminó ningún archivo**. Para la etapa de remediación posterior se identifican los siguientes elementos:

1. **`db.sqlite3` en el repositorio Git:** Debe ser removido del índice del repositorio (`git rm --cached`) y agregado a `.gitignore`.
2. **Archivos temporales en servidor HostGator:** Carpeta `/tmp` y `restart.txt` en el servidor deben mantenerse protegidos sin permisos públicos de lectura.
3. **Caché de pytest (`.pytest_cache/`):** Asegurar que no sea sincronizado al servidor de producción durante los despliegues.

---

## 10. PREGUNTA FINAL HUMM RELEASE GATE v2

> **¿Autorizarías personalmente que esta aplicación sea utilizada por los primeros usuarios reales bajo las condiciones del Pilot Envelope definido?**

# NO — NO APTO PARA PILOTO

### Fundamentación Técnica:
Ninguna aplicación —incluso en fase de MVP o piloto con pocos usuarios conocidos— puede ser autorizada mientras:
1. Su **base de datos completa sea descargable públicamente** desde internet (`https://humm.cl/FONDOS/db.sqlite3`).
2. Su **repositorio de código fuente e historial Git completo estén expuestos** a descarga abierta (`https://humm.cl/FONDOS/.git/`).
3. El **modo depuración (`DEBUG = True`) continúe activo** en el servidor de producción entregando trazas detalladas del sistema.
4. La **clave criptográfica `SECRET_KEY` sea una clave insegura pública**.
5. Exista un **script de despliegue que sobreescriba y elimine la base de datos real** al actualizar código.

Tan pronto como estos 5 bloqueadores P0 sean remediados y verificados en el servidor real, la aplicación **podrá ser recalificada inmediatamente como 🟢 APTO PARA PILOTO CONTROLADO**, dado que la calidad de su lógica determinista, templates y pruebas automatizadas es sobresaliente.

---
*Fin del Informe Oficial HUMM RELEASE GATE v2. Se suspenden acciones de remediación y cambios de código en cumplimiento estricto del protocolo de auditoría.*
