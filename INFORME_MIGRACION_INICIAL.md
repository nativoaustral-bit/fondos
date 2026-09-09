# 📊 Informe de Migración y Normalización Inicial de Fondos

Fecha de ejecución: **9 de septiembre de 2026**  
Archivo de origen: `Base_fondos_no_reembolsables_Chile_MVP-2.xlsx`  
Herramienta de conversión: `orientador/management/commands/convert_legacy_base.py`

---

## 1. Resumen Ejecutivo de la Migración

El inventario histórico proporcionado contenía 7 hojas con datos no normalizados de fondos no reembolsables en Chile. Se ejecutó el conversor automatizado desarrollado específicamente para reconocer su estructura, preservar identificadores y fechas históricas de verificación, y mapear cada registro a la base de datos canónica de **Humm Financiamiento**.

| Entidad / Tabla Canónica | Registros Procesados | Registros Creados en BD | Estado Editorial Asignado |
|---|---|---|---|
| **Entidades** | 20 | 20 | `publicado` |
| **Instrumentos** | 71 | 71 | `publicado` |
| **Convocatorias** | 35 | 35 | `publicado` |
| **Fuentes Oficiales** | 36 | 36 vinculadas a URLs | Trazables en campos de evidencia |

---

## 2. Preservación de Fechas y Trazabilidad

Conforme al mandato de la **Sección 14**, ninguna fecha de verificación fue sobrescrita con la fecha de la conversión:
* Se mantuvieron las fechas históricas registradas en el archivo (`2026-08-28`).
* Las convocatorias con fecha de cierre anterior a la fecha actual (`2026-09-08`) fueron evaluadas por el motor temporal, pasando de forma transparente al estado *"Plazo informado finalizado"*.
* Las convocatorias con cierre fijado para el día de la consulta (`2026-09-08`) activan correctamente la regla de *"Cierra hoy: confirmar hora"*.

---

## 3. Mapeo de Columnas y Transformaciones

### Hoja `Entidades`:
* `Entidad ID` &rarr; `entidad_id` (Clave primaria inmutable).
* `Entidad` &rarr; `nombre`.
* `Tipo` &rarr; `tipo` (`publica`, `privada`, `mixta`, `regional`).
* `URL oficial` &rarr; `url_oficial`.
* `Población foco` &rarr; `poblacion_foco`.

### Hoja `Instrumentos`:
* `Instrumento ID` &rarr; `instrumento_id`.
* `Entidad` &rarr; Relación de clave foránea hacia la tabla `Entidades`.
* `Instrumento` &rarr; `nombre`.
* `Tipo apoyo` &rarr; `tipo_beneficio` (`subsidio`, `voucher`, `premio`).
* `No reembolsable` &rarr; `no_reembolsable_confirmado` (`si`).
* `Etapas Humm` &rarr; Normalizado a códigos de situación (`idea`, `prototipo`, `ventas_informales`, `ventas_formales` o `todos`).
* `Formalización objetivo` &rarr; Normalizado a `cualquiera`, `sin_inicio_primera` o `con_inicio_primera`.
* `Monto máx. CLP` &rarr; `monto_max` numérico en pesos (sin símbolos ni separadores de miles).
* `% cofinanciamiento público` y `Aporte postulante` &rarr; `aporte_pct` y `aporte_descripcion`.
* `Qué financia` &rarr; Mapeo semántico de palabras clave hacia códigos de necesidad (`equipamiento`, `capital_trabajo`, `ventas_digital`, `prototipo`, `infraestructura`, `asistencia_tecnica`).
* `Requisitos clave` &rarr; `requisitos_principales`.
* `Exclusiones/alertas` &rarr; `que_no_financia`.
* `Verificado` &rarr; Fechas independientes `requisitos_verificado_en`, `montos_verificado_en`, `cobertura_verificado_en`.

### Hoja `Convocatorias`:
* `Convocatoria ID` &rarr; `convocatoria_id`.
* `Instrumento ID` &rarr; Relación foránea hacia `Instrumento`.
* `Territorio` &rarr; Mapeado a códigos territoriales oficiales ISO (`CL-LR`, `CL-LL`, `CL-AI`, `CL-MA` o `todos` para nacional).
* `Apertura` y `Cierre` &rarr; `fecha_apertura` y `fecha_cierre` (formato `YYYY-MM-DD`).
* `Estado` &rarr; `estado_fuente` (`abierta`, `cerrada`, `anunciada`, `por_confirmar`).
* Campos descriptivos heredados &rarr; Asignados con convención `HEREDAR`.

---

## 4. Campos no Mapeados y Observaciones

* **Hojas informativas auxiliares**: Las hojas `Resumen MVP` y `Campos motor` del archivo legacy contenían notas de contexto y descripciones preliminares que no forman parte de las tablas de datos operativas; sus conceptos fueron incorporados a la lógica del motor y al `DICCIONARIO_DATOS.md`.
* **Columna "Días restantes"**: No se almacena como dato estático en la base de datos, ya que el motor la calcula en tiempo real al momento de cada consulta del usuario para evitar desactualizaciones.
* **Columna "Prioridad MVP" y "Confianza"**: Se preservaron dentro de la nota de auditoría del campo `evidencia_verificacion` de cada instrumento.
