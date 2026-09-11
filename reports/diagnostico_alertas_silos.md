# Diagnóstico de las alertas de silos

Fecha de revisión: 09/09/2026. Fuente: CSV locales, unidos y deduplicados con las reglas actuales. No se modificaron cálculos, filtros ni registros. Tolerancia analizada: ±5%; nivel alto actual: valor absoluto >10%.

## Causa confirmada

En `src/components/kpi_cards.py`, `if high` convierte el estado completo del silo en rojo cuando existe al menos un registro con desviación absoluta superior a 2 × tolerancia. No utiliza proporción de incumplimiento, persistencia, tamaño de muestra ni desviación estándar. El factor 2 es una regla de presentación añadida al dashboard, no un límite de proceso validado con planta.

El valor principal de la tarjeta conserva la desviación estándar muestral de los porcentajes reportados, incluidos ceros de silos sin uso, como main. El estado usa otra población: excluye silos sin uso, objetivos cero con real no cero y porcentajes ausentes. La diferencia entre ambas poblaciones explica un sigma bajo junto a una alerta roja.

## Resultado por período

Evaluables en esta auditoría: objetivo positivo, real disponible y porcentaje disponible. En los CSV revisados no hay pesos negativos ni ausentes que produzcan diferencias con la máscara actual de alertas. Porcentaje fuera de tolerancia: número de valores con abs(pct)>5 dividido entre evaluables.

### 25/04/2026–24/06/2026 (rango inicial)

| Silo | Evaluables | Fuera ±5% | % fuera ±5% | Mayores ±10% | De esos, real cero | σ tarjeta | P95 del error absoluto |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 923 | 9 | 0.97% | 5 | 5 | 2.39 | 0.92% |
| 2 | 5,113 | 126 | 2.46% | 90 | 22 | 5.37 | 0.99% |
| 3 | 3,829 | 62 | 1.62% | 47 | 17 | 4.57 | 0.94% |
| 4 | 551 | 4 | 0.73% | 4 | 4 | 2.13 | 1.00% |
| 5 | 110 | 5 | 4.54% | 5 | 3 | 2.12 | 1.20% |
| 6 | 7,863 | 319 | 4.06% | 157 | 19 | 30.48 | 5.00% |
| 7 | 1,561 | 17 | 1.09% | 10 | 2 | 3.39 | 0.90% |
| 8 | 7,199 | 137 | 1.90% | 59 | 23 | 5.50 | 1.05% |

### 2026 hasta el 24 de junio

| Silo | Evaluables | Fuera ±5% | % fuera ±5% | Mayores ±10% | De esos, real cero | σ tarjeta | P95 del error absoluto |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4,157 | 87 | 2.09% | 37 | 18 | 2.83 | 1.39% |
| 2 | 12,407 | 391 | 3.15% | 268 | 53 | 5.40 | 1.05% |
| 3 | 12,208 | 323 | 2.65% | 232 | 44 | 4.79 | 1.06% |
| 4 | 2,218 | 17 | 0.77% | 15 | 15 | 2.53 | 1.00% |
| 5 | 458 | 12 | 2.62% | 12 | 10 | 2.16 | 1.11% |
| 6 | 19,228 | 1,012 | 5.26% | 525 | 61 | 19.72 | 6.66% |
| 7 | 9,032 | 121 | 1.34% | 64 | 22 | 3.84 | 0.95% |
| 8 | 14,031 | 275 | 1.96% | 137 | 59 | 5.25 | 1.05% |

### Histórico completo

| Silo | Evaluables | Fuera ±5% | % fuera ±5% | Mayores ±10% | De esos, real cero | σ tarjeta | P95 del error absoluto |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 37,018 | 662 | 1.79% | 383 | 249 | 2.58 | 1.80% |
| 2 | 163,403 | 3,559 | 2.18% | 2,370 | 805 | 5.91 | 0.97% |
| 3 | 221,910 | 2,737 | 1.23% | 2,059 | 928 | 5.20 | 1.01% |
| 4 | 38,380 | 719 | 1.87% | 416 | 268 | 2.68 | 1.32% |
| 5 | 124,355 | 11,500 | 9.25% | 8,422 | 495 | 7.18 | 15.29% |
| 6 | 161,375 | 11,717 | 7.26% | 6,347 | 587 | 7.12 | 8.57% |
| 7 | 115,097 | 5,508 | 4.79% | 3,118 | 669 | 4.62 | 5.00% |
| 8 | 270,700 | 23,546 | 8.70% | 16,008 | 1,011 | 9.05 | 12.72% |

## Casos que explican las alertas

- Silos 1 y 4 en el rango inicial: todos los eventos mayores de ±10% son objetivo positivo con real cero, equivalentes a −100%. Esos casos no son silos sin uso (objetivo y real cero). Debe confirmarse si representan falta de dosificación, inicio de corrida, cancelación o captura parcial.
- Silo 5 en el rango inicial: solo 110 registros evaluables. Tiene cinco eventos altos, tres con real cero. Compararlo por cantidad bruta de eventos con el silo 6 sería engañoso.
- Silo 6: dos registros del 26/05/2026, 22:31:48 y 22:35:10, batches 137 y 138, objetivo 40 kg y real 839 kg. La desviación de 1.997,5% coincide aritméticamente. Se trata de dos registros distintos, no duplicados por la clave actual. Su realidad operacional exige revisar el registro del mezclador.
- En los registros con objetivo positivo de 2026, los porcentajes reportados de los ocho silos coinciden con (real − objetivo) / objetivo × 100 dentro de 0,05 puntos. No hay evidencia de una fórmula porcentual rota que explique los ocho rojos.

## Limitaciones de interpretación

- Un semáforo rojo por cualquier evento es una alerta de existencia, no una clasificación de rendimiento del período ni un diagnóstico mecánico.
- Cuanto más histórico se selecciona, más probable es encontrar al menos un evento extremo. La etiqueta permanece roja aunque los demás resultados estén dentro de tolerancia.
- La desviación estándar da mucho peso a valores extremos. Incluir ceros de silos sin uso también cambia su interpretación, pero se mantiene para respetar main.
- El histórico mezcla recetas, materiales y etapas de operación. No permite atribuir diferencias al equipo o al operario por sí solo.
- El estado de alerta excluye objetivo cero con real no cero, pero esos porcentajes reportados todavía participan en sigma y en ciertos gráficos. Debe mantenerse explícita esta diferencia hasta acordar un criterio homogéneo.

## Corrección recomendada

1. Conservar las tarjetas sigma verificadas contra main.
2. Sustituir la etiqueta global “Desvíos altos” por información cuantitativa: porcentaje en tolerancia, eventos >±5%, eventos >±10% y tamaño de muestra. Mantener rojo en los eventos individuales.
3. Separar los eventos “objetivo positivo / real cero” de los pesajes completos, sin eliminarlos ni reclasificarlos como buenos automáticamente.
4. Mostrar calidad de datos: sin objetivo, porcentaje ausente y discrepancias aritméticas.
5. Si se desea un estado general por silo, definir con planta una tasa máxima de incumplimiento, ventana de evaluación y mínimo de muestras. No reutilizar el 5% de tolerancia de peso como si fuera automáticamente una tasa aceptable de fallos.
6. Añadir mediana y percentil 95 del error absoluto como medidas complementarias, sin reemplazar silenciosamente sigma ni excluir extremos.

## Comprobaciones adicionales

- En el rango inicial hay 95 registros de silo con objetivo positivo y real cero; 93 pertenecen a batches 0 o 1. Esto es compatible con un problema de captura o etapa de arranque, pero no prueba su causa. Son registros de silo, no 95 batches únicos.
- En el silo 6, los dos registros de 1.997,5% aportan el 96,63% de la suma de cuadrados alrededor de la media utilizada para calcular la varianza de la tarjeta. Como ejercicio de sensibilidad, retirar únicamente esos dos registros cambia sigma de 30,48 a 5,58. No se retiraron del dashboard ni del dataset.
