# Revisión del dataset y silos

Revisión: 8 de septiembre de 2026. Archivos CSV locales; no se consultó Access. No se modificaron los datos ni las reglas de cálculo.

## Cobertura

- M1: 388.825 filas y 117 columnas. M1_out: 217 filas y 120 columnas.
- Total concatenado: 389.042 filas. La regla actual elimina 239 y conserva 388.803 registros, entre 28/11/2019 y 24/06/2026.
- 2026: 23.671 registros hasta el 24 de junio; no es un año completo.
- No se encontraron fechas/horas inválidas ni pesos objetivo/reales ausentes en los silos revisados.
- Hay 232 registros sin operario y 3 sin producto. El anterior filtro que preseleccionaba todos los operarios excluía los 232 sin nombre, explicando el conteo anterior de 388.571.

## Silos en 2026

Uso: peso objetivo o real distinto de cero. Fuera de ±5%: porcentaje reportado en el CSV, sobre registros con uso. No equivale a diagnosticar una falla del equipo.

| Silo | Con uso | Sin uso | Con uso / batches | Fuera de ±5% | σ reportada |
|---|---:|---:|---:|---:|---:|
| 1 | 4,157 | 19,514 | 17.6% | 87 | 6.73% |
| 2 | 12,418 | 11,253 | 52.5% | 391 | 7.45% |
| 3 | 12,216 | 11,455 | 51.6% | 323 | 6.67% |
| 4 | 2,218 | 21,453 | 9.4% | 17 | 8.17% |
| 5 | 460 | 23,211 | 1.9% | 12 | 15.27% |
| 6 | 19,235 | 4,436 | 81.3% | 1,012 | 21.87% |
| 7 | 9,043 | 14,628 | 38.2% | 121 | 6.19% |
| 8 | 14,038 | 9,633 | 59.3% | 275 | 6.80% |
| P1 | 23,371 | 300 | 98.7% | 670 | 13.88% |

## Hallazgos prioritarios

1. **P1 está fuera de la pantalla.** Tiene 385.056 registros con uso en el histórico y 23.371 en 2026. Sus descripciones corresponden principalmente a materiales PM. Confirmar con planta qué representa P1 antes de integrarlo como otro silo o como dosificación separada. Los silos 9–12 y P2 tienen objetivo y real cero en todo el histórico.

2. **Un 0% no siempre es válido.** En los silos 1–8 hay 461 registros con objetivo cero y real distinto de cero; 46 en 2026. El porcentaje relativo al objetivo no está definido en estos casos. Deben identificarse como “Sin objetivo” y excluirse de las estadísticas porcentuales, conservando los kg y la incidencia.

3. **Silo 6 presenta extremos verificables en el CSV.** El 26/05/2026 a las 22:31:48 y 22:35:10 registra objetivo 40, real 839, diferencia 799 y 1.997,50%. La aritmética coincide; confirmar en el registro de planta si hubo sobredosificación, asignación incorrecta o captura errónea. No atribuirlo automáticamente al equipo ni borrar estos datos.

4. **Existen inconsistencias históricas puntuales.** En silos 3 y 5 hay cuatro registros por silo del 28/11/2019 con diferencias reportadas cero pese a pesos distintos. En 2026 las desviaciones de silos 1–8 con objetivo positivo coinciden con (real − objetivo) / objetivo × 100 dentro de 0,05 puntos porcentuales.

5. **P1 necesita validación específica de precisión.** Hay 53.505 diferencias en kg que se apartan más de 0,05 del cálculo real − objetivo y 3.975 diferencias porcentuales superiores a 0,05 puntos con objetivo positivo. Parte de los ejemplos muestra objetivo decimal y diferencia en kg entera, compatible con pérdida de precisión. No clasificar automáticamente todos esos registros como errores de pesaje.

6. **La deduplicación merece trazabilidad.** Solo 17 filas son duplicados exactos considerando todas las columnas; la regla por fecha, hora, big-bag, batch y operario elimina 239. Se detectó un grupo con distintos pesos en silos 3, 5 y P1. Mantener evidencia de cuál fuente prevalece antes de considerar todos los descartes duplicados idénticos.

## Interpretación de la pantalla

- “Sin pesaje” corresponde a objetivo y real cero, aunque permanezca una descripción de material.
- “Sin dato” corresponde a ausencia de desviación; no se encontraron porcentajes ausentes en los silos activos auditados.
- Objetivo positivo con real cero produce −100%; es diferente de “Sin pesaje”.
- Los nombres de material cambian dentro de un mismo silo a lo largo del histórico. La comparación entre silos mezcla materiales, recetas y períodos.
- σ mide dispersión, no error medio ni proporción de cumplimiento. Conviene mostrar el número de pesajes y el porcentaje fuera de tolerancia junto a σ.

## Siguiente paso recomendado

Etiquetar primero los registros sin objetivo; confirmar la función de P1; añadir conteos de pesajes válidos por silo y revisión trazable de extremos y conflictos entre fuentes.
