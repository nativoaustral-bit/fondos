# INFORME HUMM REMEDIATION GATE — FONDOS
### Auditoría Técnica Post-Remediación, Seguridad e Integridad Operacional
**Protocolo:** HUMM RELEASE GATE v2 + ADDENDUM v2.1  
**Fecha de Evaluación:** 11 de septiembre de 2026  
**Aplicación:** Humm Fondos (`fondos.humm.cl`)  
**Infraestructura:** HostGator Shared Hosting (cPanel) + Apache CGI/Passenger + Django 6.1.1 + SQLite 3  
**Veredicto Anterior:** 🔴 NO APTO PARA PILOTO (5 Bloqueadores P0 en Servidor Real)  

---

## 1. Veredicto de Remediación

# 🟢 APTO PARA PILOTO CONTROLADO
*(TODOS LOS HALLAZGOS P0 Y P1 HAN SIDO REMEDIADOS Y VERIFICADOS EN EL SERVIDOR REAL)*

> **Dictamen:**  
> Se han corregido el 100% de las vulnerabilidades críticas y operacionales identificadas en el *INFORME HUMM RELEASE GATE v2*.  
> La base de datos viva SQLite fue desacoplada de Git, reubicada fuera del DocumentRoot público en `/home1/paulocis/private/fondos_data/db.sqlite3` y su preservación demostrada en despliegue real.  
> El acceso perimetral a archivos sensibles (`.sqlite3`, `.git/`, `.sh`, `.env`, secretos) devuelve código `403 Forbidden` tanto en el subdominio canónico `fondos.humm.cl` como en la ruta heredada `/FONDOS/`.  
> El modo depuración `DEBUG=False` está forzado en producción con páginas de error 404/500 limpias; la `SECRET_KEY` criptográfica ha sido renovada y cargada privadamente; las cookies viajan con el flag `Secure`; se implementó el backup consistente automatizado con prueba de restauración exitosa y copia off-site; y se neutralizaron los vectores de Open Redirect, XSS y validación de entradas con una suite permanente ampliada a 50 pruebas locales aprobadas al 100%.

---

## 2. Resumen de Estados de Remediación

| Código | Hallazgo | Severidad | Clasificación | Entorno Verificado |
|---|---|:---:|:---:|:---:|
| **P0-1** | Exposición y Descarga Pública de Base de Datos (`db.sqlite3`) | P0 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL |
| **P0-2** | Exposición de Repositorio `.git/` y Script `deploy.sh` | P0 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL |
| **P0-3** | Script de Despliegue Destructivo (`git reset --hard`) | P0 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |
| **P0-4** | Modo Depuración Activo en Producción (`DEBUG = True`) | P0 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL |
| **P0-5** | `SECRET_KEY` Insegura por Defecto en Producción | P0 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |
| **P1-1** | Ausencia Total de Automatización y Procedimiento de Respaldo | P1 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |
| **P1-2** | Redirección Abierta (Open Redirect) en Login Administrativo | P1 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |
| **P1-3** | Potencial Vector XSS por `innerHTML` en Modal de Apoyo | P1 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |
| **P1-4** | Cookies de Sesión y CSRF sin Flag `Secure` en HTTPS | P1 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL |
| **P1-5** | Ausencia de Validación de Longitud y Tipos en Solicitud de Apoyo | P1 | **CORREGIDO Y VERIFICADO** | SERVIDOR REAL Y LOCAL |

---

## 3. Detalle de Remediación por Hallazgo

### [P0-1] Exposición y Descarga Pública de la Base de Datos Productiva (`db.sqlite3`)
* **ANTES:** Solicitud `curl -sI https://humm.cl/FONDOS/db.sqlite3` devolvía `HTTP/2 200` permitiendo la descarga anónima completa del archivo SQLite de 385 KB.
* **Causa Raíz:** La aplicación estaba alojada dentro de `public_html/FONDOS` y la regla de reescritura en `.htaccess` (`RewriteCond %{REQUEST_FILENAME} -f`) servía directamente cualquier archivo en disco.
* **Corrección:**
  1. La base de datos viva se movió fuera del DocumentRoot público hacia `/home1/paulocis/private/fondos_data/db.sqlite3` con permisos `700/600`.
  2. En `.htaccess` se incorporó directiva `<FilesMatch>` estricta y regla de rewrite bloqueando extensiones `.sqlite3` y variantes.
  3. La carpeta antigua `/public_html/FONDOS/` fue limpiada de archivos de base de datos.
* **DESPUÉS:** Peticiones HTTP a `db.sqlite3` son rechazadas de inmediato.
* **Evidencia:**
  ```http
  curl -sI https://humm.cl/FONDOS/db.sqlite3
  HTTP/2 403 
  server: Apache

  curl -sI https://fondos.humm.cl/db.sqlite3
  HTTP/2 403 
  server: Apache
  ```
* **Entorno:** SERVIDOR REAL (`fondos.humm.cl` y `humm.cl/FONDOS/`).
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P0-2] Exposición Pública del Repositorio Git (`.git/`) y Script de Despliegue (`deploy.sh`)
* **ANTES:** `https://humm.cl/FONDOS/.git/config` y `https://humm.cl/FONDOS/deploy.sh` devolvían `HTTP/2 200` exponiendo repositorios GitHub y credenciales SSH.
* **Causa Raíz:** Exposición directa del directorio `.git` y scripts operativos bajo `public_html/FONDOS/`.
* **Corrección:**
  1. Se trasladó el repositorio de la aplicación fuera del árbol público a `/home1/paulocis/fondos_app/`.
  2. Se eliminaron `.git/` y scripts de `/public_html/FONDOS/`.
  3. En `.htaccess` se bloquearon explícitamente directorios ocultos `^\.git` y archivos `.sh`.
* **DESPUÉS:** Solicitudes devuelven `403 Forbidden`.
* **Evidencia:**
  ```http
  curl -sI https://humm.cl/FONDOS/.git/config
  HTTP/2 403 
  server: Apache

  curl -sI https://humm.cl/FONDOS/deploy.sh
  HTTP/2 403 
  server: Apache

  curl -sI https://fondos.humm.cl/.git/config
  HTTP/2 403 
  server: Apache
  ```
* **Entorno:** SERVIDOR REAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P0-3] Script de Despliegue Destructivo Capaz de Sobreescribir la Base de Datos Productiva
* **ANTES:** `db.sqlite3` estaba rastreada en Git (`git ls-files db.sqlite3` positivo) y `deploy.sh` ejecutaba `git reset --hard origin/main`, sobreescribiendo los datos vivos con la base del repositorio.
* **Causa Raíz:** Inclusión errónea de `db.sqlite3` en el commit inicial e invocación de reset destructivo en el script de deployment.
* **Corrección:**
  1. Ejecutado `git rm --cached db.sqlite3` y agregadas reglas estrictas a `.gitignore`.
  2. Rediseñado `deploy.sh`: corre suite de tests locales previos (aborta ante fallos), genera backup preventivo con hash y conteos antes de desplegar, actualiza código con `git fetch` y `git merge --ff-only` sin tocar archivos persistentes, ejecuta migraciones y audita `PRAGMA integrity_check` y conteos post-deploy.
* **DESPUÉS:** La base persistente no reside en el repositorio y el despliegue no la sustituye.
* **Evidencia:**
  - `git ls-files db.sqlite3` → Vacío (no rastreado).
  - Estado pre-deploy en HostGator: Instrumentos: 71, Usuarios: 1, Solicitudes: 0, Hash: `c41f5bf4e2dac3be32e3fb2e45fd24f4e11d1f45bc8fc91dab1b2d598c8037a9`.
  - Estado post-deploy en HostGator: `PRAGMA integrity_check: ok`, Instrumentos: 71, Usuarios: 1, Solicitudes: 0.
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P0-4] Modo Depuración Activo en Producción (`DEBUG = True`)
* **ANTES:** `curl -s https://fondos.humm.cl/ruta-inexistente/` respondía con la página técnica oficial de depuración de Django exponiendo trazas, rutas (`ROOT_URLCONF`), variables de entorno y estructura del sistema.
* **Causa Raíz:** `settings.py` establecía `DEBUG = os.environ.get('DEBUG', 'True')` por defecto ante la falta de inyección de variables de shell por Passenger.
* **Corrección:**
  1. `settings.py` configurado con `DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')` (obligatoriamente `False` por defecto).
  2. Creadas plantillas seguras `orientador/templates/404.html` y `500.html` con identidad visual oficial de Humm sin datos técnicos.
* **DESPUÉS:** Petición a ruta inexistente responde con página 404 limpia institucional.
* **Evidencia:**
  ```html
  curl -s https://fondos.humm.cl/ruta-inexistente-debug-test-verificacion/ | grep -E "(title|h1)"
  <title>Página no encontrada — Humm Financiamiento</title>
  <h1 style="font-size: 1.5rem; margin-bottom: 16px; color: #1f2937;">Página no encontrada</h1>
  ```
* **Entorno:** SERVIDOR REAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P0-5] Clave Criptográfica `SECRET_KEY` Insegura por Defecto en Producción
* **ANTES:** `settings.py` usaba la clave hardcodeada con prefijo `django-insecure-` en producción.
* **Causa Raíz:** Falta de carga de secretos externos para el proceso WSGI de Passenger.
* **Corrección:**
  1. Implementado cargador seguro `_load_private_config()` que lee `/home1/paulocis/private/fondos_env.json` (permisos `600`).
  2. Generada nueva `SECRET_KEY` criptográficamente segura de alta entropía (64 bytes urlsafe) directamente en el servidor sin exponerla en código, repositorios ni logs.
  3. Regla en `settings.py` que lanza `ImproperlyConfigured` si en producción la clave falta o contiene `django-insecure-`.
  4. Agregada plantilla sanitizada `fondos_env.example.json` en el repositorio.
* **DESPUÉS:** La clave comprometida fue desechada; la aplicación productiva opera con clave privada segura y aborta ante claves inseguras.
* **Evidencia:**
  - Permisos en servidor: `-rw------- 1 paulocis paulocis 324 /home1/paulocis/private/fondos_env.json`.
  - Prueba local de arranque con `DEBUG=False` y clave insegura: `django.core.exceptions.ImproperlyConfigured: SECRET_KEY insegura detectada en entorno de producción.`
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P1-1] Ausencia Total de Automatización y Procedimiento de Respaldo
* **ANTES:** No existían scripts, cron ni mecanismos de respaldo para `db.sqlite3`.
* **Causa Raíz:** Falta de implementación operacional en el repositorio original.
* **Corrección:**
  1. Implementado `scripts/backup_sqlite.sh`: utiliza la API `.backup` de SQLite para consistencia ante escrituras concurrentes, compresión `gzip -9`, checksum SHA-256 y retención de 14 días en `/home1/paulocis/RESPALDOS/fondos_backups/` (permisos 700/600).
  2. Programada tarea cron diaria en cPanel: `30 3 * * * /home1/paulocis/scripts/backup_sqlite.sh >> /home1/paulocis/logs/fondos_backup_cron.log 2>&1`.
  3. Implementado `scripts/restore_sqlite.sh`: verifica checksum, descomprime y audita `PRAGMA integrity_check` y registros del catálogo.
  4. Implementado `scripts/download_offsite_backup.sh`: descarga y valida periódicamente el backup fuera de HostGator.
* **DESPUÉS:** Respaldos automáticos diarios, restauración probada y copia externa disponible.
* **Evidencia:**
  - Ejecución de `./scripts/backup_sqlite.sh` en servidor: genera archivo `.sqlite3.gz` y `.sha256`.
  - Restauración aislada con `./scripts/restore_sqlite.sh`: `PRAGMA integrity_check: ok`, Instrumentos: 71, Convocatorias: 35, Usuarios: 1.
  - Ejecución local de `./scripts/download_offsite_backup.sh`: `Integridad SHA-256 verificada localmente: 03ee37b4b050...`.
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P1-2] Redirección Abierta (Open Redirect) en Login Administrativo
* **ANTES:** `admin_login_view` redirigía a `request.GET.get('next')` sin validar el host, permitiendo phishing hacia dominios externos.
* **Causa Raíz:** Falta de saneamiento del parámetro `next`.
* **Corrección:** Validación estricta con `django.utils.http.url_has_allowed_host_and_scheme(url=raw_next, allowed_hosts={request.get_host()})`. Si el destino no es un enlace relativo o pertenece a otro host, se fuerza a `/gestion/`.
* **DESPUÉS:** URLs externas son rechazadas y neutralizadas.
* **Evidencia:**
  - Prueba en servidor real: `curl -s "https://fondos.humm.cl/gestion/login/?next=https://malicious-attacker.com"` renderiza `<input type="hidden" name="next" value="/gestion/">`.
  - Pruebas unitarias permanentes en `test_security_remediation.py` aprobadas.
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P1-3] Potencial Vector XSS por `innerHTML` en Modal de Apoyo
* **ANTES:** `orientador.js` asignaba directamente `feedbackEl.innerHTML = ... ${data.mensaje}` permitiendo la interpretación de tags HTML arbitrarios ingresados en el campo `nombre`.
* **Causa Raíz:** Uso inseguro de manipulación de cadenas en `innerHTML`.
* **Corrección:**
  1. En `orientador.js`, reemplazado `innerHTML` por manipulación segura del DOM (`textContent`, `createElement` y `createTextNode`).
  2. En `orientador/views/public.py`, el nombre es escapado con `html.escape` antes de componer el mensaje JSON.
* **DESPUÉS:** Cualquier carga útil con scripts o tags HTML es tratada como texto inofensivo.
* **Evidencia:**
  - Inyección real contra la API: enviando `nombre="<script>alert(1)</script>"`, la API devuelve:
    `"mensaje": "Gracias &lt;script&gt;alert(1)&lt;/script&gt;, hemos recibido tu solicitud..."`
    (Cero inyección de `<script>` en crudo).
  - Pruebas automatizadas en `test_security_remediation.py` aprobadas.
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P1-4] Cookies de Sesión y CSRF sin Flag `Secure` en HTTPS
* **ANTES:** Cabeceras HTTP emitían cookies sin el flag `; Secure`.
* **Causa Raíz:** Ausencia de `SESSION_COOKIE_SECURE = True` y `CSRF_COOKIE_SECURE = True` en `settings.py`.
* **Corrección:** Incorporados flags obligatorios de cookies seguras y cabeceras de hardening en `settings.py`.
* **DESPUÉS:** Ambas cookies se transmiten exclusivamente con el atributo `Secure`.
* **Evidencia:**
  ```http
  curl -sI https://fondos.humm.cl/ | grep -i "set-cookie"
  set-cookie: csrftoken=...; Path=/; SameSite=Lax; Secure
  set-cookie: sessionid=...; HttpOnly; Path=/; SameSite=Lax; Secure
  ```
* **Entorno:** SERVIDOR REAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

### [P1-5] Ausencia de Validación de Longitud y Tipos en Solicitud de Apoyo
* **ANTES:** `solicitar_apoyo_view` no comprobaba límites de longitud ni formatos, exponiendo a errores 500 no controlados ante datos extensos o malformados.
* **Causa Raíz:** Falta de capa de validación previa a la persistencia.
* **Corrección:**
  1. Validación server-side: `nombre` (1 a 150 caracteres), `contacto_valor` (3 a 150 caracteres), canal permitido (`email` o `whatsapp`), formato de email (`validate_email`), formato numérico para WhatsApp/teléfono, y longitud máxima de mensaje (2000 caracteres).
  2. Retorno de `JsonResponse({'ok': False, 'error': ...}, status=400)` controlado ante cualquier entrada no válida (cero 500s).
* **DESPUÉS:** Entradas inválidas reciben respuesta HTTP 400 limpia y estructurada.
* **Evidencia:**
  - Solicitud real con campo vacío: `HTTP 400` `{'ok': False, 'error': 'Debes ingresar tu nombre.'}`.
  - 8 pruebas de límites y formatos en `TestInputValidationLimits` aprobadas al 100%.
* **Entorno:** SERVIDOR REAL Y LOCAL.
* **Resultado:** **CORREGIDO Y VERIFICADO**.

---

## 4. Estado Integral de Verificaciones

### Resultado Total de Pruebas Automatizadas (pytest)
```
platform darwin -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
django: version: 6.1.1, settings: humm_fondos.settings
collected 50 items

orientador/tests/test_excel_contract.py .......                          [ 14%]
orientador/tests/test_matching_engine.py .........                       [ 32%]
orientador/tests/test_public_flow.py ...........                         [ 54%]
orientador/tests/test_security_remediation.py .................          [ 88%]
orientador/tests/test_status_engine.py ......                            [100%]

======================== 50 passed, 1 warning in 2.03s =========================
```
* **Pruebas Originales Conservadas:** 33 / 33 aprobadas.
* **Nuevas Pruebas de Seguridad y Hardening:** 17 / 17 aprobadas.
* **Total Suite Permanente:** **50 aprobadas / 0 fallidas (100% éxito)**.

---

### Diagnóstico de Despliegue (`python manage.py check --deploy`)
Ejecutado con la configuración real en el servidor HostGator:
```
System check identified some issues:

WARNINGS:
?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting.
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True.

System check identified 2 issues (0 silenced).
```
* Las 4 advertencias de severidad alta (W009: `SECRET_KEY`, W012: `SESSION_COOKIE_SECURE`, W016: `CSRF_COOKIE_SECURE`, W018: `DEBUG`) fueron **100% resueltas**.
* Las 2 advertencias restantes corresponden a HSTS y redirección forzada de SSL, delegadas a nivel de servidor Apache en cPanel.

---

### Estado de Respaldos y Restauración
1. **Base de Datos Persistente:** `/home1/paulocis/private/fondos_data/db.sqlite3` (Permisos `700/600`).
2. **Respaldo Automático:** Script `/home1/paulocis/scripts/backup_sqlite.sh` con `.backup` de SQLite, gzip y SHA-256, programado diariamente a las 03:30 AM en crontab.
3. **Restauración Verificada:** Probada con éxito en base aislada mediante `/home1/paulocis/scripts/restore_sqlite.sh` certificando `PRAGMA integrity_check: ok`, 71 instrumentos y 35 convocatorias.
4. **Respaldo Off-Site:** Script `./scripts/download_offsite_backup.sh` probado exitosamente, descargando y validando por SHA-256 en infraestructura local/externa.

---

### Estado del Perímetro y Archivos Públicos
* `https://fondos.humm.cl/` → Operativo (HTTP 200), cookies `Secure`.
* `https://fondos.humm.cl/db.sqlite3` → **HTTP 403 Forbidden**.
* `https://fondos.humm.cl/.git/config` → **HTTP 403 Forbidden**.
* `https://fondos.humm.cl/deploy.sh` → **HTTP 403 Forbidden**.
* `https://fondos.humm.cl/fondos_env.json` → **HTTP 403 Forbidden**.
* `https://fondos.humm.cl/gestion/` → **HTTP 302** (Redirige a login).
* `https://humm.cl/FONDOS/` → Limpia de código, DB y `.git`; bloqueada perimetralmente (**HTTP 403**).

---

### Prueba de Preservación de Base de Datos durante Despliegue
* **Antes del Despliegue:**
  - Backup preventivo generado: `pre_deploy_20260911_120516.sqlite3` (SHA-256: `c41f5bf4e2dac3be32e3fb2e45fd24f4e11d1f45bc8fc91dab1b2d598c8037a9`).
  - Instrumentos: 71, Usuarios: 1, Solicitudes: 0.
* **Después del Despliegue y Migraciones:**
  - `PRAGMA integrity_check: ok`.
  - Instrumentos: 71, Usuarios: 1, Solicitudes: 0.
  - Convocatorias: 35.
* **Veredicto:** **PRESERVACIÓN DE DATOS DEMOSTRADA AL 100%**.

---

## 5. Dictamen Final

La aplicación **Humm Fondos** cumple con la totalidad de los requisitos del **HUMM RELEASE GATE v2 + Addendum v2.1** bajo el marco definido para el MVP:
* No se modificó la infraestructura de base (HostGator + Django + SQLite).
* No se añadieron librerías ni servicios pesados (sin Redis, sin Celery, sin motores externos).
* Se remediaron de raíz los 5 bloqueadores P0 y los 5 hallazgos P1.
* Los datos productivos están aislados, protegidos y respaldados.

### Veredicto Oficial:
# 🟢 APTO PARA PILOTO CONTROLADO

*(Fin del informe. No se liberan usuarios masivos. No se agregan nuevas funcionalidades).*
