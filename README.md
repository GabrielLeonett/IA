# Agente Cognitivo para Diagnóstico y Mantenimiento Predictivo Automotriz

**Ejercicio Práctico 3** — Sistema de Razonamiento Basado en Reglas + Factores de Certeza + CBR

Arquitectura **BDI** (Beliefs-Desires-Intentions) para diagnóstico de fallas automotrices usando reglas de producción con Factores de Certeza (Shortliffe & Buchanan) y Razonamiento Basado en Casos (CBR).

---

## Requisitos

- **Python 3.10+**
- Instalar dependencias:

```bash
pip install pdfplumber
```

*(Solo necesaria si quieres re-extraer texto de los PDFs originales)*

---

## Archivos del proyecto

| Archivo | Descripción |
|---|---|
| `ejercicio3_automotriz.py` | Implementación completa del agente (~490 líneas) |
| `modelo_bdi_automotriz.puml` | Diagrama PlantUML de la ontología BDI |
| `ciclo_bdi_automotriz.puml` | Diagrama PlantUML del ciclo de razonamiento |
| `arquitectura_agente.puml` | Diagrama PlantUML de la arquitectura de componentes |
| `README.md` | Este archivo |

---

## Cómo ejecutar

```bash
python ejercicio3_automotriz.py
```

El programa te guiará paso a paso:

1. **Datos del vehículo** — marca, modelo, año, kilometraje
2. **Síntomas** — seleccionás uno o varios de un menú
3. **Códigos OBD-II** (opcional) — si conectaste un escáner
4. **Predicción de fallas futuras** — basada en kilometraje y antigüedad
5. **Diagnóstico** — el motor de inferencia procesa con reglas + FC + CBR
6. **Reporte** — explicación detallada de cada decisión y plan de acción
7. **Aprendizaje** — opción de guardar el caso para mejorar predicciones futuras

### Ejemplo de salida

```
=== DIAGNÓSTICO AUTOMOTRIZ ===

Falla principal detectada: Batería descargada o en fin de vida útil
Nivel de certeza (FC): 99.0%

[AMARILLO] URGENCIA AMARILLA: Reparar en menos de 24 horas

--- Reglas activadas para el diagnóstico ---
  * SI [dificultad_arranque=True, luces_debiles=True] -> bateria_descargada FC=0.85
  * SI [codigo_P0562=True] -> bateria_descargada FC=0.9

--- Plan de Acción Sugerido ---
  1. Verificar voltaje de batería con multímetro (>12.4V)
  2. Limpiar bornes y conexiones de batería
  3. Reemplazar batería si voltaje < 12.4V o más de 3 años

  Costo total estimado: $8,500
  Tiempo total estimado: 1.0 horas
```

---

## Diagramas PlantUML

Los archivos `.puml` se pueden visualizar con:

- **VS Code**: extensión [PlantUML](https://marketplace.visualstudio.com/items?itemName=jebbs.plantuml)
- **Online**: https://www.plantuml.com/plantuml/uml/
- **CLI**: `plantuml modelo_bdi_automotriz.puml`

---

## Estructura técnica

### Ontología (Creencias)

- `Vehiculo`, `Usuario`, `Sintoma` — datos de entrada
- `SensorOBD` — códigos DTC
- `Falla`, `NivelUrgencia` — hipótesis y priorización
- `Repuesto`, `AccionMantenimiento` — planificación
- `HistorialMantenimiento` — casos pasados

### Metas (Deseos)

1. **Seguridad** — no errar falla crítica (frenos, dirección, airbag)
2. **Efectividad** — diagnóstico correcto con FC >= 0.7
3. **Eficiencia** — minimizar costo y tiempo de reparación

### Motor de inferencia

- **Forward chaining** con 18 reglas de producción
- **Combinación confluyente**: FC₁ + FC₂ − FC₁·FC₂
- **Combinación contradictoria**: (FC₁ + FC₂) / (1 − min(|FC₁|, |FC₂|))
- **Ajuste CBR**: busca casos históricos similares y ajusta FC (±30% peso)
- **Predicción de fallas futuras** basada en reglas de desgaste por kilometraje

---

## Licencia

Proyecto académico — Ejercicio Práctico de Inteligencia Artificial.
