# 📚 Diccionario de Datos — Contrato Excel (.xlsx)

Versión del esquema: **1.1** · Compatible retroactivamente con **1.0** · Actualizado en Septiembre 2026

Este documento describe la estructura técnica, tipos de datos, códigos admitidos y reglas de negocio del archivo `.xlsx` utilizado para importar y exportar el catálogo de **Humm Financiamiento**.

---

## 1. Hoja: `Control`

Metadatos de versión y control de concurrencia del archivo.

| Columna | Tipo | Obligatorio | Descripción / Ejemplo |
|---|---|---|---|
| `schema_version` | Texto | Sí | Versión del esquema del archivo (`1.1` actual; el importador también acepta `1.0`). |
| `catalog_base_version` | Entero | Sí | Número de versión secuencial de la base de datos desde la que se exportó (ej. `1`, `2`). |
| `exported_at` | Fecha ISO | Sí | Momento exacto de la exportación en formato ISO (ej. `2026-09-09T15:01:30.346Z`). |

---

## 2. Hoja: `Entidades`

Instituciones u organismos que administran o financian los programas.

| Columna | Tipo | Obligatorio | Valores Permitidos | Descripción |
|---|---|---|---|---|
| `entidad_id` | Texto | Sí | Único e inmutable | Identificador estable (ej. `ENT-001`, `ENT-003`, `ENT-008`). |
| `nombre` | Texto | Sí | Texto libre | Nombre oficial de la institución (ej. `Sercotec`, `Corfo`, `FIA`). |
| `tipo` | Código | Sí | `publica`, `privada`, `mixta`, `academia`, `sociedad_civil` | Naturaleza jurídica de la institución. |
| `url_oficial` | URL | Sí | `https://...` | Portal web principal de la entidad. |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Solo `publicado` es visible al público. |

---

## 3. Hoja: `Instrumentos` (34 columnas en Esquema 1.1)

Programas de apoyo o líneas de financiamiento de referencia.

| Columna | Tipo | Obligatorio | Valores Permitidos | Descripción |
|---|---|---|---|---|
| `instrumento_id` | Texto | Sí | Único e inmutable | Identificador del programa (ej. `INS-001`, `INS-008`). |
| `entidad_id` | Texto | Sí | Debe existir en Entidades | Identificador de la entidad administradora. |
| `nombre` | Texto | Sí | Texto libre | Nombre del instrumento (ej. `Capital Semilla Emprende`). |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Solo `publicado` aparece en consultas públicas. |
| `resumen` | Texto | No | Texto libre | Resumen breve de compatibilidad. |
| `dirigido_a` | Texto | No | Texto libre | Perfil del postulante y público objetivo. |
| `que_financia` | Texto | No | Texto libre | Conceptos financiables (activos, insumos, etc.). |
| `que_no_financia` | Texto | No | Texto libre | Gastos excluidos o prohibidos por bases. |
| `requisitos_principales` | Texto | No | Texto libre | Condiciones clave de admisibilidad. |
| `siguiente_paso` | Texto | No | Texto libre | Tarea recomendada para preparar la postulación. |
| `necesidades` | Códigos | Sí | `equipamiento`, `capital_trabajo`, `ventas_digital`, `prototipo`, `infraestructura`, `asistencia_tecnica`, `produccion_cultural`, o `todos` | Códigos separados por punto y coma (`;`). |
| `situaciones` | Códigos | Sí (Histórico) | `idea`, `prototipo`, `ventas_informales`, `ventas_formales`, o `todos` | Madurez histórica. En Formulario v2 se evalúa formalización + ventas. |
| `rubros` | Códigos | Sí | `alimentos`, `comercio`, `servicios`, `turismo`, `agropecuario`, `pesca`, `cultura`, `tecnologia`, `otro`, o `todos` | Sectores productivos aceptados. |
| `cobertura` | Código | Sí | `nacional`, `regional`, `comunal`, `por_confirmar` | Cobertura territorial de referencia. |
| `regiones` | Códigos | Sí | Códigos ISO (ej. `CL-LR;CL-LL`) o `todos` | Regiones aplicables separadas por punto y coma. |
| `comunas` | Texto | No | Texto libre | Comunas específicas si aplica. |
| `formalizacion_requerida` | Código | Sí | `sin_inicio_primera`, `con_inicio_primera`, `formalizacion_declarada`, `cualquiera`, `por_confirmar` | Requisito tributario ante el SII. |
| `tipo_beneficio` | Código | Sí | `subsidio`, `premio`, `bonificacion`, `voucher`, `en_especie`, `beca` | Naturaleza del beneficio entregado. |
| `no_reembolsable_confirmado` | Código | Sí | `si`, `no`, `por_confirmar` | **Solo `si` puede ser publicado en el catálogo del MVP.** |
| `modalidad_entrega` | Código | Sí | `anticipo`, `contra_gastos`, `en_especie`, `mixta`, `por_confirmar` | Cómo se entrega el subsidio. |
| `monto_min` | Número | No | Decimal positivo o vacío | Monto mínimo referencial. |
| `monto_max` | Número | No | Decimal positivo o vacío | Monto máximo referencial. |
| `moneda` | Código | Sí | `CLP`, `UF`, `UTM` | Moneda oficial. Conservar la original sin convertir. |
| `monto_condiciones` | Texto | No | Texto libre | Aclaraciones sobre tramos o condiciones de entrega. |
| `aporte_pct` | Número | No | Decimal (0 a 100) | Porcentaje de cofinanciamiento propio exigido. |
| `aporte_base` | Código | Sí | `subsidio`, `costo_total`, `por_confirmar` | Sobre qué base se calcula el porcentaje de aporte propio. |
| `aporte_descripcion` | Texto | No | Texto libre | Explicación en lenguaje simple del aporte propio. |
| `url_programa` | URL | No | `https://...` | Ficha oficial permanente del programa. |
| `requisitos_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación de requisitos. |
| `montos_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación de montos y aportes. |
| `cobertura_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación de cobertura territorial. |
| `evidencia_verificacion` | Texto | No | Texto libre | Notas y respaldo de la fuente consultada. |
| `objetivos` *(Nuevo v1.1)* | Códigos | No | `iniciar_negocio`, `fortalecer_negocio`, `vender_digitalizar`, `desarrollar_innovacion`, `sostenibilidad`, `proyecto_cultural` | Códigos separados por punto y coma (`;`). |
| `ventas_requeridas` *(Nuevo v1.1)* | Código | Sí | `si`, `no`, `indiferente`, `por_confirmar` | `si`: exige ventas; `no`: exige no registrar ventas; `indiferente`: ambas. |

---

## 4. Hoja: `Convocatorias` (39 columnas en Esquema 1.1)

Llamados específicos en el tiempo y territorio vinculados a un instrumento.

Admite `HEREDAR` en los campos correspondientes para adoptar automáticamente el valor del instrumento padre.

| Columna | Tipo | Obligatorio | Valores Permitidos | Convención |
|---|---|---|---|---|
| `convocatoria_id` | Texto | Sí | Único e inmutable | Identificador del llamado (ej. `CONV-001`). |
| `instrumento_id` | Texto | Sí | Debe existir en Instrumentos | Instrumento al que pertenece. |
| `nombre` | Texto | Sí | Texto libre | Nombre de la convocatoria (ej. `Semilla Los Ríos 2026`). |
| `estado_editorial` | Código | Sí | `borrador`, `publicado`, `archivado` | Estado de publicación. |
| `dirigido_a` | Texto | No | Texto o `HEREDAR` | Específico o heredado. |
| `que_financia` | Texto | No | Texto o `HEREDAR` | Específico o heredado. |
| `que_no_financia` | Texto | No | Texto o `HEREDAR` | Específico o heredado. |
| `requisitos_principales` | Texto | No | Texto o `HEREDAR` | Específico o heredado. |
| `necesidades` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `situaciones` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `rubros` | Códigos | No | Códigos o `HEREDAR` | Específico o heredado. |
| `cobertura` | Código | No | `nacional`, `regional`, `comunal` o `HEREDAR` | Cobertura territorial del llamado. |
| `regiones` | Códigos | No | Códigos territoriales o `HEREDAR` | Regiones donde rige este llamado. |
| `comunas` | Texto | No | Texto libre | Comunas específicas si aplica. |
| `formalizacion_requerida` | Código | No | Códigos tributarios o `HEREDAR` | Condición tributaria de este llamado. |
| `modalidad_entrega` | Código | No | Códigos de entrega o `HEREDAR` | Específico o heredado. |
| `monto_min` | Número | No | Decimal positivo o vacío | Específico del llamado (no admite HEREDAR). |
| `monto_max` | Número | No | Decimal positivo o vacío | Específico del llamado (no admite HEREDAR). |
| `moneda` | Código | Sí | `CLP`, `UF`, `UTM` | Moneda oficial del llamado. |
| `monto_condiciones` | Texto | No | Texto libre | Condiciones específicas del llamado. |
| `aporte_pct` | Número | No | Decimal (0 a 100) | Aporte propio específico. |
| `aporte_base` | Código | Sí | `subsidio`, `costo_total`, `por_confirmar` | Base del cálculo de aporte. |
| `aporte_descripcion` | Texto | No | Texto libre | Explicación del aporte en este llamado. |
| `fecha_apertura` | Fecha | No | `YYYY-MM-DD` | Fecha oficial de inicio de postulaciones. |
| `hora_apertura` | Hora | No | `HH:MM` | Hora de apertura si se conoce. |
| `fecha_cierre` | Fecha | No | `YYYY-MM-DD` | Fecha oficial de cierre de postulaciones. |
| `hora_cierre` | Hora | No | `HH:MM` | Hora de cierre si se conoce. |
| `zona_horaria` | Texto | Sí | `America/Santiago`, `America/Punta_Arenas` | Zona horaria IANA de Chile. |
| `cierre_modalidad` | Código | Sí | `fecha_definida`, `permanente`, `hasta_agotar`, `sin_confirmar` | Tipo de cierre. |
| `estado_fuente` | Código | Sí | `anunciada`, `abierta`, `cerrada`, `suspendida`, `cancelada`, `por_confirmar` | Estado observado en la fuente oficial. |
| `url_convocatoria` | URL | No | `https://...` | Enlace directo a las bases y postulación oficial. |
| `requisitos_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación técnica. |
| `montos_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación técnica. |
| `cobertura_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación técnica. |
| `fechas_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación técnica. |
| `estado_verificado_en` | Fecha ISO | No | `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DD` | Fecha de verificación técnica. |
| `evidencia_verificacion` | Texto | No | Texto libre | Notas y evidencia de la convocatoria. |
| `objetivos` *(Nuevo v1.1)* | Códigos | No | Códigos de objetivo, `todos` o `HEREDAR` | Específico o heredado del instrumento. |
| `ventas_requeridas` *(Nuevo v1.1)* | Código | Sí | `si`, `no`, `indiferente`, `por_confirmar`, `HEREDAR` | Específico o heredado del instrumento. |

---

## 5. Códigos de Regiones Oficiales de Chile (ISO 3166-2:CL)

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
