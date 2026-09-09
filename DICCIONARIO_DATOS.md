# 📚 Diccionario de Datos — Contrato Excel (.xlsx)

Versión del esquema: **1.0** · Septiembre 2026

Este documento describe la estructura técnica, tipos de datos, códigos admitidos y reglas de negocio del archivo `.xlsx` utilizado para importar y exportar el catálogo de **Humm Financiamiento**.

---

## 1. Hoja: `Control`

Metadatos de versión y trazabilidad del archivo.

| Columna | Tipo | Obligatorio | Descripción / Ejemplo |
|---|---|---|---|
| `schema_version` | Texto | Sí | Versión del esquema del archivo. Debe ser `1.0`. |
| `catalog_base_version` | Entero | Sí | Número de versión secuencial de la base de datos desde la que se exportó (ej. `1`, `2`). |
| `exported_at` | Fecha ISO | Sí | Momento exacto de la exportación (ej. `2026-09-08T22:00:00Z`). |

---

## 2. Hoja: `Entidades`

Instituciones u organismos que administran o financian los programas.

| Columna | Tipo | Obligatorio | Valores Permitidos | Descripción |
|---|---|---|---|---|
| `entidad_id` | Texto | Sí | Único e inmutable | Identificador estable (ej. `ENT-001`, `sercotec`, `corfo`). |
| `nombre` | Texto | Sí | Texto libre | Nombre oficial de la institución (ej. `FOSIS`, `Sercotec`). |
| `tipo` | Código | Sí | `publica`, `privada`, `mixta`, `regional`, `otra` | Naturaleza jurídica de la institución. |
| `url_oficial` | URL | Sí | `https://...` | Portal web principal de la entidad. |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Solo `publicado` es visible al público. |

---

## 3. Hoja: `Instrumentos`

Programas de apoyo o líneas de financiamiento de referencia.

| Columna | Tipo | Obligatorio | Valores Permitidos | Descripción |
|---|---|---|---|---|
| `instrumento_id` | Texto | Sí | Único e inmutable | Identificador del programa (ej. `INS-001`, `semilla-inicia`). |
| `entidad_id` | Texto | Sí | Debe existir en Entidades | Identificador de la entidad administradora. |
| `nombre` | Texto | Sí | Texto libre | Nombre del instrumento (ej. `Capital Semilla Emprende`). |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Solo `publicado` aparece en consultas públicas. |
| `resumen` | Texto | No | Texto libre | Resumen breve de compatibilidad. |
| `dirigido_a` | Texto | No | Texto libre | Perfil del postulante y público objetivo. |
| `que_financia` | Texto | No | Texto libre | Conceptos financiables (activos, insumos, etc.). |
| `que_no_financia` | Texto | No | Texto libre | Gastos excluidos o prohibidos. |
| `requisitos_principales` | Texto | No | Texto libre | Condiciones clave de admisibilidad. |
| `siguiente_paso` | Texto | No | Texto libre | Tarea recomendada para preparar la postulación. |
| `necesidades` | Códigos | Sí | `equipamiento`, `capital_trabajo`, `ventas_digital`, `prototipo`, `infraestructura`, `asistencia_tecnica`, o `todos` | Códigos separados por punto y coma (`;`). |
| `situaciones` | Códigos | Sí | `idea`, `prototipo`, `ventas_informales`, `ventas_formales`, o `todos` | Etapas en que aplica el instrumento. |
| `rubros` | Códigos | Sí | `alimentos`, `comercio`, `servicios`, `turismo`, `agro_rural`, `pesca`, `cultura_artesania`, `tecnologia`, `otro`, o `todos` | Sectores productivos aceptados. |
| `cobertura` | Código | Sí | `nacional`, `regional`, `comunal`, `por_confirmar` | Cobertura territorial de referencia. |
| `regiones` | Códigos | Sí | Códigos ISO (ej. `CL-LR;CL-LL`) o `todos` | Regiones aplicables separadas por punto y coma. |
| `comunas` | Texto | No | Texto libre | Comunas específicas si aplica. |
| `formalizacion_requerida` | Código | Sí | `cualquiera`, `formalizacion_declarada`, `sin_inicio_primera`, `con_inicio_primera`, `por_confirmar` | Requisito tributario ante el SII. |
| `tipo_beneficio` | Código | Sí | `subsidio`, `premio`, `bonificacion`, `voucher`, `en_especie`, `beca` | Naturaleza del beneficio entregado. |
| `no_reembolsable_confirmado` | Código | Sí | `si`, `no`, `por_confirmar` | **Solo `si` puede ser publicado en el catálogo del MVP.** |
| `modalidad_entrega` | Código | Sí | `anticipo`, `contra_gastos`, `en_especie`, `mixta`, `por_confirmar` | Cómo se entrega el financiamiento. |
| `monto_min` | Número | No | Decimal positivo o vacío | Monto mínimo referencial. |
| `monto_max` | Número | No | Decimal positivo o vacío | Monto máximo referencial. |
| `moneda` | Código | Sí | `CLP`, `UF`, `UTM` | Moneda oficial. Conservar la original sin convertir. |
| `monto_condiciones` | Texto | No | Texto libre | Aclaraciones sobre tramos o condiciones de entrega. |
| `aporte_pct` | Número | No | Decimal (0 a 100) | Porcentaje de cofinanciamiento que debe aportar el postulante. |
| `aporte_base` | Código | Sí | `subsidio`, `costo_total`, `por_confirmar` | Sobre qué base se calcula el porcentaje de aporte propio. |
| `aporte_descripcion` | Texto | No | Texto libre | Explicación en lenguaje simple del aporte propio. |
| `url_programa` | URL | No | `https://...` | Ficha oficial permanente del programa. |
| `*_verificado_en` | Fecha | No | `YYYY-MM-DD` o ISO | Fechas de comprobación de requisitos, montos y cobertura. |
| `evidencia_verificacion` | Texto | No | Texto libre | Notas y respaldo de la fuente consultada. |

---

## 4. Hoja: `Convocatorias`

Llamados específicos en el tiempo y territorio vinculados a un instrumento.

| Columna | Tipo | Obligatorio | Valores Permitidos | Convención |
|---|---|---|---|---|
| `convocatoria_id` | Texto | Sí | Único e inmutable | Identificador del llamado (ej. `CONV-001`). |
| `instrumento_id` | Texto | Sí | Debe existir en Instrumentos | Instrumento al que pertenece. |
| `nombre` | Texto | Sí | Texto libre | Nombre de la convocatoria (ej. `Semilla Los Ríos 2026`). |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Estado de publicación. |
| `dirigido_a` | Texto | No | Texto o `HEREDAR` | Específico o heredado del instrumento. |
| `que_financia` | Texto | No | Texto o `HEREDAR` | Específico o heredado del instrumento. |
| `que_no_financia` | Texto | No | Texto o `HEREDAR` | Específico o heredado del instrumento. |
| `requisitos_principales` | Texto | No | Texto o `HEREDAR` | Específico o heredado del instrumento. |
| `necesidades` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `situaciones` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `rubros` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `cobertura` | Código | No | `nacional`, `regional`, `comunal` o `HEREDAR` | Cobertura territorial del llamado. |
| `regiones` | Códigos | No | Códigos territoriales o `HEREDAR` | Regiones donde rige este llamado. |
| `comunas` | Texto | No | Texto libre | Comunas específicas si aplica. |
| `formalizacion_requerida` | Código | No | Códigos tributarios o `HEREDAR` | Condición tributaria de este llamado. |
| `fecha_apertura` | Fecha | No | `YYYY-MM-DD` | Fecha oficial de inicio de postulaciones. |
| `hora_apertura` | Hora | No | `HH:MM` | Hora de apertura si se conoce. |
| `fecha_cierre` | Fecha | No | `YYYY-MM-DD` | Fecha oficial de cierre de postulaciones. |
| `hora_cierre` | Hora | No | `HH:MM` | Hora de cierre si se conoce. |
| `zona_horaria` | Texto | Sí | `America/Santiago`, `America/Punta_Arenas` | Zona horaria IANA de Chile. |
| `cierre_modalidad` | Código | Sí | `fecha_definida`, `permanente`, `hasta_agotar`, `sin_confirmar` | Tipo de cierre. |
| `estado_fuente` | Código | Sí | `anunciada`, `abierta`, `cerrada`, `suspendida`, `cancelada`, `por_confirmar` | Estado observado en la fuente oficial. |
| `url_convocatoria` | URL | No | `https://...` | Enlace directo a las bases y postulación oficial. |
| `*_verificado_en` | Fecha | No | `YYYY-MM-DD` o ISO | Fechas de comprobación de requisitos, fechas y estado. |

---

## 5. Códigos de Regiones Oficiales de Chile

| Código | Región |
|---|---|
| `CL-AP` | Arica y Parinacota |
| `CL-TA` | Tarapacá |
| `CL-AN` | Antofagasta |
| `CL-AT` | Atacama |
| `CL-CO` | Coquimbo |
| `CL-VA` | Valparaíso |
| `CL-RM` | Metropolitana de Santiago |
| `CL-OH` | Libertador General Bernardo O'Higgins |
| `CL-ML` | Maule |
| `CL-NB` | Ñuble |
| `CL-BI` | Biobío |
| `CL-AR` | La Araucanía |
| `CL-LR` | Los Ríos |
| `CL-LL` | Los Lagos |
| `CL-AI` | Aysén del General Carlos Ibáñez del Campo |
| `CL-MA` | Magallanes y de la Antártica Chilena |
