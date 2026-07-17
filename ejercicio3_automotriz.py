"""
Agente Cognitivo para Diagnóstico y Mantenimiento Predictivo Automotriz
Ejercicio Práctico 3 - Sistema Basado en Reglas + FC + CBR + Gemini + Inventario

Arquitectura BDI:
  - Creencias: Base de Conocimiento (reglas, ontología, casos históricos, inventario)
  - Deseos: Seguridad > Efectividad > Eficiencia
  - Intenciones: Percepcion -> Filtro -> Razonamiento -> Planificacion -> Actuacion

Funcionalidades:
  1. Diagnóstico de fallas basado en síntomas + OBD-II
  2. Predicción de fallas futuras usando datos históricos y patrones de desgaste
  3. Recomendaciones de mantenimiento priorizando seguridad, costo y disponibilidad
  4. Gestión de inventario de repuestos basado en predicciones de demanda
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


# =============================================================================
# ONTOLOGÍA (Creencias)
# =============================================================================

@dataclass
class Vehiculo:
    vin: str
    marca: str
    modelo: str
    anio: int
    kilometraje: float

    def descripcion(self) -> str:
        return f"{self.marca} {self.modelo} ({self.anio}) - {self.kilometraje:.0f} km"


@dataclass
class Sintoma:
    id: str
    descripcion: str
    severidad: int = 5
    presente: bool = True


@dataclass
class CodigoOBD:
    codigo: str
    descripcion_oficial: str
    presente: bool = True


@dataclass
class AccionMantenimiento:
    descripcion: str
    costo_estimado: float = 0.0
    tiempo_estimado_horas: float = 0.0


@dataclass
class Diagnostico:
    fallas: list[tuple[str, float]]
    urgencia: str
    plan_accion: list[AccionMantenimiento]
    explicacion: str
    sugerencias_ia: str = ""
    estado_inventario: str = ""


# =============================================================================
# REGLA (Producción con Factor de Certeza)
# =============================================================================

@dataclass
class Regla:
    condiciones: dict[str, bool | float | str]
    conclusion: str
    fc: float
    explicacion: str

    def evaluar(self, hechos: dict) -> Optional[float]:
        for clave, valor_esperado in self.condiciones.items():
            valor_real = hechos.get(clave)
            if valor_real is None:
                return None
            if isinstance(valor_esperado, bool):
                if bool(valor_real) != valor_esperado:
                    return None
            elif isinstance(valor_esperado, (int, float)):
                if float(valor_real) < float(valor_esperado):
                    return None
            else:
                if str(valor_real).lower() != str(valor_esperado).lower():
                    return None
        return self.fc


# =============================================================================
# BASE DE CONOCIMIENTO (Reglas)
# =============================================================================

class BaseConocimiento:
    def __init__(self):
        self.reglas: list[Regla] = []
        self._cargar_reglas()

    def _cargar_reglas(self):
        self.reglas = [
            # === SISTEMA ELÉCTRICO ===
            Regla({"dificultad_arranque": True, "luces_debiles": True},
                  "bateria_descargada", 0.85,
                  "Dificultad de arranque junto con luces débiles es altamente sugestivo de batería descargada."),
            Regla({"dificultad_arranque": True, "testigo_bateria": True},
                  "bateria_descargada", 0.80,
                  "El testigo de batería encendido durante el arranque indica que el sistema eléctrico no está recibiendo voltaje adecuado."),
            Regla({"ruido_chirrido": True, "luces_debiles": True},
                  "alternador_danado", 0.80,
                  "Ruido chirriante del alternador junto con luces débiles indica que el alternador no genera carga suficiente."),
            Regla({"testigo_bateria": True, "luces_debiles": True},
                  "alternador_danado", 0.75,
                  "Testigo de batería + luces débiles con motor en marcha sugiere falla en el alternador."),
            # === SISTEMA DE ENCENDIDO ===
            Regla({"testigo_motor": True, "tirones_aceleracion": True},
                  "bujia_deteriorada", 0.70,
                  "Testigo del motor con tirones al acelerar indica fallo de encendido por bujías desgastadas."),
            Regla({"perdida_potencia": True, "humo_negro_escape": True},
                  "filtro_aire_tapado", 0.75,
                  "Pérdida de potencia con humo negro indica mezcla rica por restricción en la entrada de aire."),
            # === SISTEMA MECÁNICO ===
            Regla({"vibracion": True, "ruido_metalico": True},
                  "correa_distribucion_desgastada", 0.80,
                  "Vibración anormal con ruido metálico del motor sugiere desgaste en la correa de distribución."),
            Regla({"humo_negro_escape": True, "olor_gasolina": True},
                  "inyector_sucio", 0.70,
                  "Humo negro con olor a gasolina sin quemar indica mala atomización por inyectores sucios."),
            # === SISTEMA DE FRENOS ===
            Regla({"freno_blando": True, "ruido_frenado": True},
                  "freno_desgastado", 0.85,
                  "Pedal de freno blando con ruido metálico al frenar indica desgaste crítico de pastillas o discos."),
            # === SISTEMA DE REFRIGERACIÓN ===
            Regla({"sobrecalentamiento": True, "perdida_refrigerante": True},
                  "termostato_danado", 0.75,
                  "Sobrecalentamiento con pérdida de refrigerante sugiere termostato atascado o fuga en el sistema."),
            # === SISTEMA DE COMBUSTIBLE ===
            Regla({"testigo_motor": True, "consumo_excesivo": True},
                  "sonda_lambda_danada", 0.70,
                  "Testigo del motor con consumo excesivo indica lectura incorrecta de la sonda lambda."),
            Regla({"perdida_potencia": True, "testigo_motor": True},
                  "valvula_egr_tapada", 0.65,
                  "Pérdida de potencia con testigo del motor puede indicar válvula EGR obstruida."),
            # === SISTEMA DE DIRECCIÓN ===
            Regla({"direccion_dura": True, "ruido_direccion": True},
                  "bomba_direccion_danada", 0.75,
                  "Dirección dura con ruido al girar indica baja presión en la bomba de dirección asistida."),
            # === CÓDIGOS OBD-II ===
            Regla({"codigo_P0562": True}, "bateria_descargada", 0.90,
                  "Código P0562: System Voltage Low."),
            Regla({"codigo_P0300": True}, "bujia_deteriorada", 0.85,
                  "Código P0300: Random Misfire Detectado."),
            Regla({"codigo_P0171": True}, "sonda_lambda_danada", 0.80,
                  "Código P0171: System Too Lean."),
            Regla({"codigo_P0420": True}, "catalizador_danado", 0.85,
                  "Código P0420: Catalyst Efficiency Below Threshold."),
            Regla({"codigo_P0401": True}, "valvula_egr_tapada", 0.80,
                  "Código P0401: EGR Flow Insufficient."),
            # === REGLA PREDICTIVA ===
            Regla({"kilometraje_alto": True, "ultimo_cambio_aceite": True},
                  "cambio_aceite_proximo", 0.70,
                  "Alto kilometraje desde último cambio de aceite. Programar cambio preventivo."),
        ]

    def obtener_reglas_por_conclusion(self, conclusion: str) -> list[Regla]:
        return [r for r in self.reglas if r.conclusion == conclusion]


# =============================================================================
# MOTOR DE INFERENCIA (Forward Chaining + Shortliffe-Buchanan)
# =============================================================================

class MotorInferencia:
    @staticmethod
    def combinar_confluyente(fc1: float, fc2: float) -> float:
        return fc1 + fc2 - fc1 * fc2

    @staticmethod
    def combinar_contradictorio(fc1: float, fc2: float) -> float:
        return (fc1 + fc2) / (1 - min(abs(fc1), abs(fc2)))

    def forward_chaining(self, hechos: dict, bc: BaseConocimiento) -> dict[str, float]:
        conclusiones: dict[str, list[float]] = {}
        for regla in bc.reglas:
            fc_resultado = regla.evaluar(hechos)
            if fc_resultado is not None and abs(fc_resultado) >= 0.2:
                if regla.conclusion not in conclusiones:
                    conclusiones[regla.conclusion] = []
                conclusiones[regla.conclusion].append(fc_resultado)

        fc_final: dict[str, float] = {}
        for conclusion, fcs in conclusiones.items():
            if not fcs:
                continue
            positivos = [f for f in fcs if f > 0]
            negativos = [f for f in fcs if f < 0]
            fc_total = 0.0
            if positivos:
                fc_pos = positivos[0]
                for f in positivos[1:]:
                    fc_pos = self.combinar_confluyente(fc_pos, f)
                fc_total = fc_pos
            if negativos:
                fc_neg = negativos[0]
                for f in negativos[1:]:
                    fc_neg = self.combinar_confluyente(fc_neg, f)
                if positivos and negativos:
                    fc_total = self.combinar_contradictorio(fc_pos, fc_neg)
                elif negativos:
                    fc_total = fc_neg
            fc_final[conclusion] = round(max(-1.0, min(1.0, fc_total)), 3)

        return dict(sorted(fc_final.items(), key=lambda x: -x[1]))


# =============================================================================
# GESTOR CBR (Case-Based Reasoning)
# =============================================================================

@dataclass
class CasoHistorico:
    vehiculo_info: str
    sintomas: list[str]
    kilometraje: float
    falla_diagnosticada: str
    fc_obtenido: float
    accion_realizada: str
    exitoso: bool
    fecha: str = ""

    def __post_init__(self):
        if not self.fecha:
            self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class GestorCasosCBR:
    def __init__(self, archivo: str = "casos_historicos.json"):
        self.archivo = archivo
        self.casos: list[CasoHistorico] = []
        self._cargar()

    def _cargar(self):
        if os.path.exists(self.archivo):
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.casos = [CasoHistorico(**d) for d in datos]
                return
            except Exception:
                pass
        self._cargar_casos_ejemplo()
        self._guardar()

    def _cargar_casos_ejemplo(self):
        self.casos = [
            CasoHistorico("Ford Focus 2019", ["dificultad_arranque", "luces_debiles"],
                          85000, "bateria_descargada", 0.92, "Reemplazo de batería", True,
                          "2025-06-15 10:30:00"),
            CasoHistorico("Chevrolet Onix 2020", ["testigo_motor", "tirones_aceleracion"],
                          62000, "bujia_deteriorada", 0.78, "Cambio de bujías", True,
                          "2025-07-20 14:15:00"),
            CasoHistorico("Volkswagen Gol 2018", ["freno_blando", "ruido_frenado"],
                          110000, "freno_desgastado", 0.88, "Reemplazo pastillas + discos", True,
                          "2025-08-10 09:00:00"),
            CasoHistorico("Toyota Corolla 2021", ["testigo_motor", "consumo_excesivo"],
                          45000, "sonda_lambda_danada", 0.72, "Reemplazo sonda lambda", True,
                          "2025-09-05 11:45:00"),
            CasoHistorico("Fiat Cronos 2017", ["ruido_chirrido", "luces_debiles"],
                          95000, "alternador_danado", 0.81, "Reconstrucción alternador", False,
                          "2025-10-12 16:30:00"),
            CasoHistorico("Renault Sandero 2020", ["perdida_potencia", "humo_negro_escape"],
                          78000, "filtro_aire_tapado", 0.76, "Cambio filtro de aire", True,
                          "2025-11-01 08:20:00"),
        ]

    def _guardar(self):
        try:
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump([c.__dict__ for c in self.casos], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [!] Error al guardar casos: {e}")

    def buscar_similares(self, sintomas: set, top_n: int = 3) -> list[CasoHistorico]:
        def similitud(caso: CasoHistorico) -> float:
            sintomas_caso = set(s.lower() for s in caso.sintomas)
            interseccion = len(sintomas & sintomas_caso)
            union = len(sintomas | sintomas_caso)
            return interseccion / union if union > 0 else 0.0

        casos_ordenados = sorted(self.casos, key=similitud, reverse=True)
        return [c for c in casos_ordenados if similitud(c) > 0][:top_n]

    def ajustar_fc_con_cbr(self, falla: str, fc_base: float, sintomas: set) -> float:
        similares = self.buscar_similares(sintomas)
        if not similares:
            return fc_base
        casos_falla = [c for c in similares if c.falla_diagnosticada == falla]
        if not casos_falla:
            return fc_base
        tasa_exito = sum(1 for c in casos_falla if c.exitoso) / len(casos_falla)
        fc_cbr = tasa_exito * 0.3
        fc_final = fc_base * 0.7 + fc_cbr
        return round(min(1.0, fc_final), 3)

    def aprender_caso(self, caso: CasoHistorico):
        self.casos.append(caso)
        self._guardar()

    def obtener_frecuencia_fallas(self) -> dict[str, int]:
        freq: dict[str, int] = {}
        for c in self.casos:
            freq[c.falla_diagnosticada] = freq.get(c.falla_diagnosticada, 0) + 1
        return freq

    def fallas_mas_comunes(self, top_n: int = 5) -> list[tuple[str, int]]:
        freq = self.obtener_frecuencia_fallas()
        return sorted(freq.items(), key=lambda x: -x[1])[:top_n]


# =============================================================================
# GESTOR DE INVENTARIO
# =============================================================================

class GestorInventario:
    def __init__(self, archivo: str = "inventario_repuestos.json"):
        self.archivo = archivo
        self.inventario: dict = {}
        self._cargar()

    def _cargar(self):
        if os.path.exists(self.archivo):
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    self.inventario = json.load(f)
                return
            except Exception:
                pass
        self._cargar_inventario_ejemplo()
        self._guardar()

    def _cargar_inventario_ejemplo(self):
        self.inventario = {
            "bateria_descargada": {
                "repuestos": [
                    {"nombre": "Batería 12V 60Ah", "stock": 3, "precio": 8500,
                     "proveedor": "Bosch", "stock_minimo": 2, "tiempo_entrega_dias": 1}
                ]
            },
            "alternador_danado": {
                "repuestos": [
                    {"nombre": "Alternador reconstruido", "stock": 2, "precio": 18500,
                     "proveedor": "Denso", "stock_minimo": 1, "tiempo_entrega_dias": 3}
                ]
            },
            "bujia_deteriorada": {
                "repuestos": [
                    {"nombre": "Juego de bujías (4 uds)", "stock": 5, "precio": 4500,
                     "proveedor": "NGK", "stock_minimo": 2, "tiempo_entrega_dias": 1}
                ]
            },
            "filtro_aire_tapado": {
                "repuestos": [
                    {"nombre": "Filtro de aire", "stock": 5, "precio": 1500,
                     "proveedor": "Mann-Filter", "stock_minimo": 3, "tiempo_entrega_dias": 1}
                ]
            },
            "correa_distribucion_desgastada": {
                "repuestos": [
                    {"nombre": "Kit distribución (correa + tensor)", "stock": 1, "precio": 32000,
                     "proveedor": "Contitech", "stock_minimo": 2, "tiempo_entrega_dias": 4}
                ]
            },
            "inyector_sucio": {
                "repuestos": [
                    {"nombre": "Aditivo limpiador inyectores", "stock": 8, "precio": 800,
                     "proveedor": "STP", "stock_minimo": 5, "tiempo_entrega_dias": 1},
                    {"nombre": "Inyector de combustible", "stock": 2, "precio": 7000,
                     "proveedor": "Bosch", "stock_minimo": 1, "tiempo_entrega_dias": 2}
                ]
            },
            "freno_desgastado": {
                "repuestos": [
                    {"nombre": "Juego pastillas de freno", "stock": 1, "precio": 4500,
                     "proveedor": "TRW", "stock_minimo": 3, "tiempo_entrega_dias": 2},
                    {"nombre": "Disco de freno", "stock": 2, "precio": 4000,
                     "proveedor": "TRW", "stock_minimo": 2, "tiempo_entrega_dias": 2}
                ]
            },
            "termostato_danado": {
                "repuestos": [
                    {"nombre": "Termostato", "stock": 3, "precio": 3500,
                     "proveedor": "Gates", "stock_minimo": 2, "tiempo_entrega_dias": 1}
                ]
            },
            "sonda_lambda_danada": {
                "repuestos": [
                    {"nombre": "Sonda lambda", "stock": 2, "precio": 9500,
                     "proveedor": "Bosch", "stock_minimo": 1, "tiempo_entrega_dias": 2}
                ]
            },
            "valvula_egr_tapada": {
                "repuestos": [
                    {"nombre": "Válvula EGR", "stock": 1, "precio": 18000,
                     "proveedor": "Pierburg", "stock_minimo": 1, "tiempo_entrega_dias": 3}
                ]
            },
            "bomba_direccion_danada": {
                "repuestos": [
                    {"nombre": "Bomba de dirección asistida", "stock": 1, "precio": 22000,
                     "proveedor": "ZF", "stock_minimo": 1, "tiempo_entrega_dias": 4}
                ]
            },
            "catalizador_danado": {
                "repuestos": [
                    {"nombre": "Catalizador universal", "stock": 0, "precio": 45000,
                     "proveedor": "Walker", "stock_minimo": 1, "tiempo_entrega_dias": 5}
                ]
            },
            "cambio_aceite_proximo": {
                "repuestos": [
                    {"nombre": "Aceite 5W30 (5L)", "stock": 10, "precio": 3500,
                     "proveedor": "Shell", "stock_minimo": 5, "tiempo_entrega_dias": 1},
                    {"nombre": "Filtro de aceite", "stock": 8, "precio": 800,
                     "proveedor": "Mann-Filter", "stock_minimo": 5, "tiempo_entrega_dias": 1}
                ]
            },
            "herramientas": {
                "items": [
                    {"nombre": "Escaner OBD-II", "stock": 2, "stock_minimo": 1, "precio": 0},
                    {"nombre": "Multimetro digital", "stock": 3, "stock_minimo": 1, "precio": 0},
                    {"nombre": "Juego de llaves mixtas", "stock": 2, "stock_minimo": 1, "precio": 0},
                    {"nombre": "Gato hidraulico 2T", "stock": 1, "stock_minimo": 1, "precio": 0},
                    {"nombre": "Compresor de aire", "stock": 0, "stock_minimo": 1, "precio": 0}
                ]
            }
        }

    def _guardar(self):
        try:
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump(self.inventario, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [!] Error al guardar inventario: {e}")

    def verificar_disponibilidad(self, falla_id: str) -> list[dict]:
        entrada = self.inventario.get(falla_id, {})
        repuestos = entrada.get("repuestos", [])
        for r in repuestos:
            r["disponible"] = r["stock"] > 0
            r["alerta_stock"] = r["stock"] <= r.get("stock_minimo", 1)
        return repuestos

    def consumir_repuesto(self, falla_id: str, indice: int = 0) -> bool:
        entrada = self.inventario.get(falla_id)
        if not entrada:
            return False
        repuestos = entrada.get("repuestos", [])
        if indice >= len(repuestos):
            return False
        if repuestos[indice]["stock"] <= 0:
            return False
        repuestos[indice]["stock"] -= 1
        self._guardar()
        return True

    def predecir_demanda(self, casos_frecuencia: dict[str, int]) -> list[dict]:
        alertas = []
        for falla_id, falla_info in self.inventario.items():
            demanda = casos_frecuencia.get(falla_id, 0)
            for r in falla_info.get("repuestos", []):
                stock = r["stock"]
                minimo = r.get("stock_minimo", 1)
                if stock <= minimo or demanda > stock:
                    alertas.append({
                        "falla": falla_id,
                        "repuesto": r["nombre"],
                        "stock": stock,
                        "minimo": minimo,
                        "demanda_estimada": max(demanda, 1),
                        "proveedor": r["proveedor"],
                        "tiempo_entrega": r.get("tiempo_entrega_dias", 1)
                    })
        return alertas

    def resumen_inventario(self) -> str:
        lineas = []
        for falla_id, info in self.inventario.items():
            for r in info.get("repuestos", []):
                estado = "[OK]" if r["stock"] > r.get("stock_minimo", 1) else \
                         "[!]" if r["stock"] > 0 else "[X]"
                lineas.append(
                    f"  {estado} {r['nombre']:40s} stock: {r['stock']:2d} | "
                    f"mín: {r.get('stock_minimo', 1)} | ${r['precio']:>5,.0f}"
                )
        if not lineas:
            return "  (vacío)"
        return "\n".join(lineas)

    def resumen_herramientas(self) -> str:
        lineas = []
        herramientas = self.inventario.get("herramientas", {}).get("items", [])
        for h in herramientas:
            estado = "DISPONIBLE" if h["stock"] > h.get("stock_minimo", 1) else \
                     "STOCK BAJO" if h["stock"] > 0 else "AGOTADO"
            icono = "[OK]" if h["stock"] > h.get("stock_minimo", 1) else \
                    "[!]" if h["stock"] > 0 else "[NO]"
            lineas.append(
                f"  {icono} {h['nombre']:30s} stock: {h['stock']:2d}  [{estado}]"
            )
        if not lineas:
            return "  (sin herramientas registradas)"
        return "\n".join(lineas)

    def verificar_herramienta(self, nombre: str) -> dict | None:
        herramientas = self.inventario.get("herramientas", {}).get("items", [])
        for h in herramientas:
            if h["nombre"].lower() == nombre.lower():
                return {
                    "nombre": h["nombre"],
                    "disponible": h["stock"] > 0,
                    "stock": h["stock"],
                    "stock_minimo": h.get("stock_minimo", 1)
                }
        return None

    def consumir_herramienta(self, nombre: str) -> bool:
        herramientas = self.inventario.get("herramientas", {}).get("items", [])
        for h in herramientas:
            if h["nombre"].lower() == nombre.lower():
                if h["stock"] <= 0:
                    return False
                h["stock"] -= 1
                self._guardar()
                return True
        return False

    def stock_critico(self) -> list[dict]:
        criticos = []
        # Revisar herramientas
        herramientas = self.inventario.get("herramientas", {}).get("items", [])
        for h in herramientas:
            if h["stock"] <= 0:
                criticos.append({
                    "tipo": "herramienta",
                    "nombre": h["nombre"],
                    "stock": h["stock"],
                    "minimo": h.get("stock_minimo", 1)
                })
            elif h["stock"] <= h.get("stock_minimo", 1):
                criticos.append({
                    "tipo": "herramienta",
                    "nombre": h["nombre"],
                    "stock": h["stock"],
                    "minimo": h.get("stock_minimo", 1),
                    "alerta": "stock bajo"
                })
        # Revisar repuestos
        for falla_id, info in self.inventario.items():
            if falla_id == "herramientas":
                continue
            for r in info.get("repuestos", []):
                if r["stock"] <= 0:
                    criticos.append({
                        "tipo": "repuesto",
                        "falla": falla_id,
                        "nombre": r["nombre"],
                        "stock": r["stock"],
                        "minimo": r.get("stock_minimo", 1)
                    })
                elif r["stock"] <= r.get("stock_minimo", 1):
                    criticos.append({
                        "tipo": "repuesto",
                        "falla": falla_id,
                        "nombre": r["nombre"],
                        "stock": r["stock"],
                        "minimo": r.get("stock_minimo", 1),
                        "alerta": "stock bajo"
                    })
        return criticos

    def resumen_taller(self) -> str:
        lineas = [
            "",
            "--- HERRAMIENTAS DEL TALLER ---",
            self.resumen_herramientas(),
        ]
        criticos = self.stock_critico()
        if criticos:
            lineas.extend([
                "",
                "--- ALERTAS CRITICAS ---",
            ])
            for c in criticos:
                if c.get("alerta") == "stock bajo":
                    lineas.append(
                        f"  [!]  {c['nombre']} — stock: {c['stock']}, "
                        f"minimo: {c['minimo']} — REPONER PRONTO"
                    )
                else:
                    lineas.append(
                        f"  [NO] {c['nombre']} — SIN STOCK (minimo: {c['minimo']})"
                    )
        return "\n".join(lineas)


# =============================================================================
# EXPLICADOR
# =============================================================================

class Explicador:
    DESCRIPCION_FALLAS = {
        "bateria_descargada": "Batería descargada o en fin de vida útil",
        "alternador_danado": "Alternador dañado o con regulador defectuoso",
        "bujia_deteriorada": "Bujías desgastadas o en mal estado",
        "filtro_aire_tapado": "Filtro de aire obstruido",
        "correa_distribucion_desgastada": "Correa de distribución desgastada",
        "inyector_sucio": "Inyectores de combustible sucios",
        "freno_desgastado": "Pastillas o discos de freno desgastados",
        "termostato_danado": "Termostato del sistema de refrigeración defectuoso",
        "sonda_lambda_danada": "Sensor de oxígeno (sonda lambda) defectuoso",
        "valvula_egr_tapada": "Válvula EGR obstruida por carbonilla",
        "bomba_direccion_danada": "Bomba de dirección asistida con baja presión",
        "catalizador_danado": "Catalizador con eficiencia reducida",
        "cambio_aceite_proximo": "Cambio de aceite próximo según kilometraje",
    }

    URGENCIA_FALLAS = {
        "freno_desgastado": "Rojo",
        "bomba_direccion_danada": "Rojo",
        "bateria_descargada": "Amarillo",
        "alternador_danado": "Amarillo",
        "correa_distribucion_desgastada": "Amarillo",
        "termostato_danado": "Amarillo",
        "catalizador_danado": "Amarillo",
        "bujia_deteriorada": "Verde",
        "filtro_aire_tapado": "Verde",
        "inyector_sucio": "Verde",
        "sonda_lambda_danada": "Verde",
        "valvula_egr_tapada": "Verde",
        "cambio_aceite_proximo": "Verde",
    }

    SISTEMAS = {
        "bateria_descargada": "Eléctrico",
        "alternador_danado": "Eléctrico",
        "bujia_deteriorada": "Encendido",
        "filtro_aire_tapado": "Admisión",
        "correa_distribucion_desgastada": "Motor",
        "inyector_sucio": "Combustible",
        "freno_desgastado": "Frenos",
        "termostato_danado": "Refrigeración",
        "sonda_lambda_danada": "Combustible",
        "valvula_egr_tapada": "Emisiones",
        "bomba_direccion_danada": "Dirección",
        "catalizador_danado": "Emisiones",
        "cambio_aceite_proximo": "Mantenimiento",
    }

    PLANES_ACCION = {
        "bateria_descargada": [
            AccionMantenimiento("Verificar voltaje de batería con multímetro (>12.4V)", 0, 0.25),
            AccionMantenimiento("Limpiar bornes y conexiones de batería", 0, 0.25),
            AccionMantenimiento("Reemplazar batería si voltaje < 12.4V o más de 3 años", 8500, 0.5),
        ],
        "alternador_danado": [
            AccionMantenimiento("Verificar tensión de correa del alternador", 0, 0.25),
            AccionMantenimiento("Medir voltaje de salida del alternador (13.5-14.5V)", 0, 0.25),
            AccionMantenimiento("Reemplazar o reconstruir alternador según diagnóstico", 18500, 2.0),
        ],
        "bujia_deteriorada": [
            AccionMantenimiento("Inspeccionar estado de bujías (color, desgaste)", 0, 0.5),
            AccionMantenimiento("Reemplazar juego completo de bujías", 4500, 1.0),
            AccionMantenimiento("Verificar bobinas de encendido si el problema persiste", 0, 0.5),
        ],
        "filtro_aire_tapado": [
            AccionMantenimiento("Inspeccionar visualmente el filtro de aire", 0, 0.15),
            AccionMantenimiento("Reemplazar filtro de aire", 1500, 0.25),
            AccionMantenimiento("Verificar conductos de admisión", 0, 0.25),
        ],
        "correa_distribucion_desgastada": [
            AccionMantenimiento("Inspeccionar visualmente correa de distribución (grietas, desgaste)", 0, 0.5),
            AccionMantenimiento("Reemplazar correa de distribución + tensor", 32000, 4.0),
        ],
        "inyector_sucio": [
            AccionMantenimiento("Realizar limpieza de inyectores con aditivo", 800, 0.15),
            AccionMantenimiento("Limpieza ultrasónica de inyectores en banco", 6500, 2.0),
            AccionMantenimiento("Reemplazar inyectores si persiste obstrucción", 28000, 3.0),
        ],
        "freno_desgastado": [
            AccionMantenimiento("Inspeccionar espesor de pastillas de freno", 0, 0.25),
            AccionMantenimiento("Reemplazar pastillas de freno delanteras o traseras", 8500, 1.5),
            AccionMantenimiento("Verificar y rectificar discos si es necesario", 4500, 1.0),
        ],
        "termostato_danado": [
            AccionMantenimiento("Verificar temperatura de funcionamiento del motor", 0, 0.25),
            AccionMantenimiento("Reemplazar termostato", 3500, 1.0),
            AccionMantenimiento("Revisar nivel de refrigerante y purgar sistema", 0, 0.5),
        ],
        "sonda_lambda_danada": [
            AccionMantenimiento("Leer códigos de falla con escáner OBD", 0, 0.15),
            AccionMantenimiento("Reemplazar sonda lambda (sensor de oxígeno)", 9500, 1.0),
        ],
        "valvula_egr_tapada": [
            AccionMantenimiento("Limpiar válvula EGR con limpiador de carbón", 2500, 1.5),
            AccionMantenimiento("Reemplazar válvula EGR si está dañada", 18000, 2.0),
        ],
        "bomba_direccion_danada": [
            AccionMantenimiento("Verificar nivel de líquido de dirección", 0, 0.15),
            AccionMantenimiento("Reemplazar bomba de dirección asistida", 22000, 2.5),
        ],
        "catalizador_danado": [
            AccionMantenimiento("Diagnóstico con escáner OBD (código P0420)", 0, 0.25),
            AccionMantenimiento("Reemplazar catalizador", 45000, 3.0),
        ],
        "cambio_aceite_proximo": [
            AccionMantenimiento("Cambio de aceite de motor + filtro", 3500, 0.5),
            AccionMantenimiento("Inspección general de 30 puntos", 0, 0.5),
        ],
    }

    def obtener_urgencia(self, fallas: dict) -> str:
        for falla in fallas:
            if self.URGENCIA_FALLAS.get(falla, "Verde") == "Rojo":
                return "Rojo"
        for falla in fallas:
            if self.URGENCIA_FALLAS.get(falla, "Verde") == "Amarillo":
                return "Amarillo"
        return "Verde"

    def priorizar_por_seguridad(self, fallas: dict) -> list[tuple[str, float]]:
        orden = {"Rojo": 0, "Amarillo": 1, "Verde": 2}
        items = [(f, fc, orden.get(self.URGENCIA_FALLAS.get(f, "Verde"), 3))
                 for f, fc in fallas.items()]
        items.sort(key=lambda x: (x[2], -x[1]))
        return [(f, fc) for f, fc, _ in items]

    def generar_explicacion(self, fallas: dict, reglas_activadas: list[Regla],
                            sugerencias_ia: str = "") -> str:
        if not fallas:
            return "No se pudo determinar una falla con suficiente certeza."

        fallas_priorizadas = self.priorizar_por_seguridad(fallas)
        principal = fallas_priorizadas[0]
        urgencia = self.obtener_urgencia(fallas)
        etiqueta_urgencia = {
            "Rojo": "[ROJO] URGENCIA ROJA: Atención inmediata requerida (< 1 hora)",
            "Amarillo": "[AMARILLO] URGENCIA AMARILLA: Reparar en menos de 24 horas",
            "Verde": "[VERDE] URGENCIA VERDE: Mantenimiento programable",
        }

        partes = [
            "==══════════════════════════════════════════════════════==",
            "||          DIAGNÓSTICO AUTOMOTRIZ                     ||",
            "==══════════════════════════════════════════════════════==",
            "",
            f"[F] Falla principal: {self.DESCRIPCION_FALLAS.get(principal[0], principal[0])}",
            f"[FC] Certeza (FC): {principal[1]:.1%}",
            f"[!]  {etiqueta_urgencia.get(urgencia, '')}",
            "",
        ]

        partes.append("[L] Reglas activadas:")
        for falla_nombre, _ in fallas_priorizadas[:3]:
            reglas_falla = [r for r in reglas_activadas if r.conclusion == falla_nombre]
            for r in reglas_falla:
                conds = ", ".join(f"{k}={v}" for k, v in r.condiciones.items())
                partes.append(f"  • SI [{conds}] -> {falla_nombre} (FC={r.fc})")

        if sugerencias_ia:
            partes.extend(["", "[AI] Análisis mejorado por IA:", "", sugerencias_ia])

        if len(fallas) > 1:
            partes.extend(["", "[L] Otras fallas consideradas:"])
            for nombre, fc in list(fallas_priorizadas)[1:4]:
                desc = self.DESCRIPCION_FALLAS.get(nombre, nombre)
                sist = self.SISTEMAS.get(nombre, "")
                partes.append(f"  • {desc} [{sist}] — FC={fc:.1%}")

        return "\n".join(partes)

    def obtener_plan(self, fallas: dict) -> list[AccionMantenimiento]:
        acciones: list[AccionMantenimiento] = []
        vistos: set = set()
        fallas_priorizadas = self.priorizar_por_seguridad(fallas)
        for falla in fallas_priorizadas:
            plan = self.PLANES_ACCION.get(falla[0], [])
            for accion in plan:
                if accion.descripcion not in vistos:
                    acciones.append(accion)
                    vistos.add(accion.descripcion)
        return acciones


# =============================================================================
# GESTOR LLM (Gemini)
# =============================================================================

class GestorLLM:
    def __init__(self, api_key: str = None, modelo: str = "gemini-2.0-flash-lite"):
        self.disponible = False
        if not api_key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.modelo = genai.GenerativeModel(modelo)
            self.disponible = True
        except Exception as e:
            print(f"  [!] Error al inicializar Gemini: {e}")

    def _consultar(self, prompt: str) -> str:
        if not self.disponible:
            return ""
        try:
            respuesta = self.modelo.generate_content(prompt)
            return respuesta.text.strip()
        except Exception as e:
            return f"[Error al consultar Gemini: {e}]"

    def mejorar_diagnostico(self, fallas: dict, sintomas: list, vehiculo: Optional[Vehiculo],
                            reglas_activadas: list[Regla]) -> str:
        if not self.disponible or not fallas:
            return ""
        falla_principal = list(fallas.items())[0]
        sintomas_str = ", ".join(str(s) for s in sintomas)
        vehiculo_str = vehiculo.descripcion() if vehiculo else "No especificado"

        prompt = f"""Eres un experto en diagnóstico automotriz. Analiza el siguiente caso y proporciona un análisis detallado.

Vehículo: {vehiculo_str}
Síntomas reportados: {sintomas_str}
Falla principal detectada por reglas: {falla_principal[0]} (Certeza: {falla_principal[1]:.1%})

Reglas que se activaron:
{chr(10).join(f"  - {r.explicacion}" for r in reglas_activadas[:5])}

Proporciona:
1. Un análisis detallado de por qué se llegó a este diagnóstico (máximo 3 líneas)
2. Causas adicionales posibles que las reglas podrían no estar cubriendo
3. Recomendaciones para confirmar el diagnóstico antes de proceder

Sé conciso, directo y en español."""
        return self._consultar(prompt)

    def generar_reporte_final(self, diagnostico, predicciones, inventario_status) -> str:
        if not self.disponible:
            return ""
        prompt = f"""Eres un asesor automotriz. Genera un resumen ejecutivo del siguiente reporte de diagnóstico:

Fallas detectadas: {diagnostico.fallas}
Urgencia: {diagnostico.urgencia}
Plan de acción: {[a.descripcion for a in diagnostico.plan_accion[:3]]}
Predicciones futuras: {predicciones}
Estado de inventario: {inventario_status}

Genera 2-3 recomendaciones finales priorizando seguridad, costo y disponibilidad. Sé breve y en español."""
        return self._consultar(prompt)


# =============================================================================
# AGENTE AUTOMOTRIZ (Núcleo BDI)
# =============================================================================

class AgenteAutomotriz:
    def __init__(self, api_key: str = None):
        self.bc = BaseConocimiento()
        self.motor = MotorInferencia()
        self.cbr = GestorCasosCBR()
        self.explicador = Explicador()
        self.inventario = GestorInventario()
        self.llm = GestorLLM(api_key)
        self.ultimas_reglas_activadas: list[Regla] = []
        self.ultimo_diagnostico: Optional[Diagnostico] = None

    def diagnosticar(self,
                     sintomas: list[Sintoma],
                     codigos_obd: list[CodigoOBD] | None = None,
                     vehiculo: Vehiculo | None = None) -> Diagnostico:
        hechos: dict = {}

        for s in sintomas:
            hechos[s.id] = s.presente
            if s.severidad > 7:
                hechos[f"{s.id}_severidad_alta"] = True

        if codigos_obd:
            for codigo in codigos_obd:
                hechos[f"codigo_{codigo.codigo}"] = codigo.presente

        if vehiculo:
            hechos["kilometraje"] = vehiculo.kilometraje
            if vehiculo.kilometraje > 80000:
                hechos["kilometraje_alto"] = True

        # Forward chaining
        fallas_fc = self.motor.forward_chaining(hechos, self.bc)

        self.ultimas_reglas_activadas = [
            r for r in self.bc.reglas
            if r.evaluar(hechos) is not None and abs(r.evaluar(hechos)) >= 0.2
        ]

        umbral = 0.2
        fallas_filtradas = {k: v for k, v in fallas_fc.items() if abs(v) >= umbral}

        # Ajuste CBR
        sintomas_presentes = {s.id for s in sintomas if s.presente}
        for falla in list(fallas_filtradas.keys()):
            fallas_filtradas[falla] = self.cbr.ajustar_fc_con_cbr(
                falla, fallas_filtradas[falla], sintomas_presentes
            )

        fallas_ordenadas = dict(sorted(fallas_filtradas.items(), key=lambda x: -x[1]))

        # Gemini enhancement
        sugerencias_ia = ""
        if self.llm.disponible:
            sugerencias_ia = self.llm.mejorar_diagnostico(
                fallas_ordenadas,
                [s.descripcion for s in sintomas],
                vehiculo,
                self.ultimas_reglas_activadas
            )

        urgencia = self.explicador.obtener_urgencia(fallas_ordenadas)
        plan = self.explicador.obtener_plan(fallas_ordenadas)
        explicacion = self.explicador.generar_explicacion(
            fallas_ordenadas, self.ultimas_reglas_activadas, sugerencias_ia
        )

        # Inventory status
        inventario_status = self._generar_estado_inventario(fallas_ordenadas)

        self.ultimo_diagnostico = Diagnostico(
            fallas=list(fallas_ordenadas.items()),
            urgencia=urgencia,
            plan_accion=plan,
            explicacion=explicacion,
            sugerencias_ia=sugerencias_ia,
            estado_inventario=inventario_status,
        )
        return self.ultimo_diagnostico

    def _generar_estado_inventario(self, fallas: dict) -> str:
        lineas = []

        # Herramientas necesarias para el diagnostico
        herramientas_necesarias = {
            "bateria_descargada": ["Multimetro digital"],
            "alternador_danado": ["Multimetro digital"],
            "bujia_deteriorada": ["Juego de llaves mixtas"],
            "filtro_aire_tapado": ["Juego de llaves mixtas"],
            "correa_distribucion_desgastada": ["Juego de llaves mixtas", "Gato hidraulico 2T"],
            "inyector_sucio": ["Juego de llaves mixtas"],
            "freno_desgastado": ["Juego de llaves mixtas", "Gato hidraulico 2T"],
            "termostato_danado": ["Juego de llaves mixtas"],
            "sonda_lambda_danada": ["Juego de llaves mixtas"],
            "valvula_egr_tapada": ["Juego de llaves mixtas"],
            "bomba_direccion_danada": ["Juego de llaves mixtas", "Gato hidraulico 2T"],
            "catalizador_danado": ["Escaner OBD-II", "Gato hidraulico 2T"],
            "cambio_aceite_proximo": ["Juego de llaves mixtas", "Gato hidraulico 2T"],
        }

        for falla_id in fallas:
            repuestos = self.inventario.verificar_disponibilidad(falla_id)
            if repuestos:
                nom_falla = self.explicador.DESCRIPCION_FALLAS.get(falla_id, falla_id)
                lineas.append(f"  [{nom_falla}]")

                # Repuestos
                for r in repuestos:
                    icono = "[OK]" if r.get("disponible") else "[X]"
                    alerta = ""
                    if r.get("alerta_stock") and r.get("disponible"):
                        alerta = " [!] Stock bajo"
                    elif not r.get("disponible"):
                        alerta = " [X] AGOTADO — Solicitar pedido"
                    lineas.append(
                        f"    {icono} {r['nombre']} — ${r['precio']:,} "
                        f"(stock: {r['stock']}){alerta}"
                    )

                # Herramientas necesarias
                herramientas = herramientas_necesarias.get(falla_id, [])
                if herramientas:
                    lineas.append(f"    🛠️  Herramientas requeridas:")
                    for h_nombre in herramientas:
                        h_info = self.inventario.verificar_herramienta(h_nombre)
                        if h_info:
                            icono_h = "[OK]" if h_info["disponible"] else "[NO]"
                            estado_h = "" if h_info["disponible"] else " — SIN STOCK"
                            lineas.append(
                                f"      {icono_h} {h_info['nombre']} "
                                f"(stock: {h_info['stock']}){estado_h}"
                            )

        if not lineas:
            return "  No hay repuestos asociados a las fallas detectadas."
        return "\n".join(lineas)

    def predecir_fallas(self, vehiculo: Vehiculo) -> list[tuple[str, float, str]]:
        predicciones: list[tuple[str, float, str]] = []

        antiguedad = datetime.now().year - vehiculo.anio

        if vehiculo.kilometraje > 80000:
            fc = min(0.6 + 0.005 * (vehiculo.kilometraje - 80000) / 1000, 0.9)
            predicciones.append((
                "correa_distribucion_desgastada", round(fc, 2),
                "Correa de distribución cercana al cambio recomendado (80.000-100.000 km)."
            ))

        if antiguedad >= 5:
            fc = min(0.5 + 0.1 * (antiguedad - 5), 0.9)
            predicciones.append((
                "bateria_descargada", round(fc, 2),
                f"Batería con más de {antiguedad} años. Reemplazo preventivo recomendado."
            ))

        if vehiculo.kilometraje > 60000:
            predicciones.append((
                "bujia_deteriorada", 0.5,
                "Bujías con alto kilometraje (>60.000 km). Inspección recomendada."
            ))

        if vehiculo.kilometraje > 50000:
            predicciones.append((
                "cambio_aceite_proximo", 0.75,
                "Verificar intervalo de cambio de aceite según manual del fabricante."
            ))

        # Fallas basadas en casos históricos (CBR)
        fallas_comunes = self.cbr.fallas_mas_comunes(3)
        for falla, count in fallas_comunes:
            if falla not in [p[0] for p in predicciones]:
                nombre = self.explicador.DESCRIPCION_FALLAS.get(falla, falla)
                predicciones.append((
                    falla, min(0.3 + 0.1 * count, 0.8),
                    f"Falla recurrente en casos históricos ({count} ocurrencias). "
                    "Revisión preventiva sugerida."
                ))

        return predicciones

    def generar_reporte(self) -> str:
        if not self.ultimo_diagnostico:
            return "No hay diagnóstico previo."

        d = self.ultimo_diagnostico
        costo_total = sum(a.costo_estimado for a in d.plan_accion)
        tiempo_total = sum(a.tiempo_estimado_horas for a in d.plan_accion)

        freq = self.cbr.obtener_frecuencia_fallas()
        alertas_inv = self.inventario.predecir_demanda(freq)

        lineas = [
            "=" * 60,
            "   REPORTE DE DIAGNÓSTICO - AGENTE COGNITIVO AUTOMOTRIZ",
            "=" * 60,
            f"  Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"  Urgencia: {d.urgencia}",
            "",
            "--- Fallas Detectadas ---",
        ]

        for nombre, fc in d.fallas:
            desc = self.explicador.DESCRIPCION_FALLAS.get(nombre, nombre)
            sist = self.explicador.SISTEMAS.get(nombre, "")
            barra = "#" * int(abs(fc) * 20) + "." * (20 - int(abs(fc) * 20))
            lineas.append(f"  {desc:35s} [{sist:12s}] |{barra}| FC={fc:+.2f}")

        lineas.extend([
            "",
            "--- Estado de Inventario ---",
            d.estado_inventario,
        ])

        # Seccion de herramientas del taller
        lineas.extend([
            "",
            self.inventario.resumen_taller(),
            "",
            "--- Plan de Acción Sugerido ---",
        ])
        for i, accion in enumerate(d.plan_accion, 1):
            lineas.append(
                f"  {i}. {accion.descripcion} "
                f"(${accion.costo_estimado:,.0f}, {accion.tiempo_estimado_horas:.1f}h)"
            )

        lineas.extend([
            "",
            f"  Costo total estimado: ${costo_total:,.0f}",
            f"  Tiempo total estimado: {tiempo_total:.1f} horas",
        ])

        if alertas_inv:
            lineas.extend([
                "",
                "[B] Alertas de Inventario (predicción de demanda):",
            ])
            for a in alertas_inv:
                nom = self.explicador.DESCRIPCION_FALLAS.get(a["falla"], a["falla"])
                lineas.append(
                    f"  [!]  {a['repuesto']} — stock: {a['stock']}, "
                    f"mín: {a['minimo']}, demanda est.: {a['demanda_estimada']}"
                )
                lineas.append(
                    f"      Proveedor: {a['proveedor']} "
                    f"(entrega: {a['tiempo_entrega']} días)"
                )

        if d.sugerencias_ia:
            lineas.extend([
                "",
                "--- Análisis Mejorado por IA ---",
                "",
                d.sugerencias_ia,
            ])

        lineas.extend(["", "=" * 60])
        return "\n".join(lineas)


# =============================================================================
# DEMO INTERACTIVA
# =============================================================================

SINTOMAS_DISPONIBLES = {
    "1": Sintoma("dificultad_arranque", "Dificultad para arrancar el motor"),
    "2": Sintoma("luces_debiles", "Luces delanteras o tablero débiles"),
    "3": Sintoma("testigo_bateria", "Testigo de batería encendido en el tablero"),
    "4": Sintoma("ruido_chirrido", "Ruido chirriante debajo del capó"),
    "5": Sintoma("testigo_motor", "Testigo Check Engine encendido"),
    "6": Sintoma("tirones_aceleracion", "Tirones al acelerar"),
    "7": Sintoma("perdida_potencia", "Pérdida de potencia del motor"),
    "8": Sintoma("humo_negro_escape", "Humo negro saliendo del escape"),
    "9": Sintoma("vibracion", "Vibraciones anormales del vehículo"),
    "10": Sintoma("ruido_metalico", "Ruido metálico proveniente del motor"),
    "11": Sintoma("olor_gasolina", "Olor a gasolina dentro o fuera del vehículo"),
    "12": Sintoma("freno_blando", "Pedal de freno blando o esponjoso"),
    "13": Sintoma("ruido_frenado", "Ruido metálico al frenar"),
    "14": Sintoma("sobrecalentamiento", "El motor se sobrecalienta"),
    "15": Sintoma("perdida_refrigerante", "Pérdida de líquido refrigerante"),
    "16": Sintoma("consumo_excesivo", "Consumo excesivo de combustible"),
    "17": Sintoma("direccion_dura", "Dirección dura o difícil de girar"),
    "18": Sintoma("ruido_direccion", "Ruido (gemido) al girar la dirección"),
}

CODIGOS_OBD = {
    "P0562": CodigoOBD("P0562", "System Voltage Low - Bajo voltaje"),
    "P0300": CodigoOBD("P0300", "Random Misfire - Fallo encendido aleatorio"),
    "P0171": CodigoOBD("P0171", "System Too Lean - Mezcla pobre"),
    "P0420": CodigoOBD("P0420", "Catalyst Efficiency - Catalizador bajo rendimiento"),
    "P0401": CodigoOBD("P0401", "EGR Flow - Flujo EGR insuficiente"),
}


def mostrar_menu(opciones: dict, titulo: str, multi: bool = True) -> list[str]:
    print(f"\n{titulo}")
    print("-" * 50)
    for key, value in opciones.items():
        print(f"  [{key}] {value if isinstance(value, str) else value.descripcion}")
    if multi:
        print("  [0] Terminar selección")
    print()
    seleccionadas: list[str] = []
    while True:
        op = input("  Opción: ").strip()
        if op == "salir" or op == "0":
            break
        if op in opciones:
            seleccionadas.append(op)
            if not multi:
                break
        else:
            print("  Opción inválida. Escriba '0' o 'salir' para terminar.")
            if not multi:
                break
    return seleccionadas


def demo():
    print()
    print("=" * 60)
    print("   AGENTE COGNITIVO PARA DIAGNÓSTICO AUTOMOTRIZ")
    print("   Sistema Basado en Reglas + FC + CBR + IA + Inventario")
    print("=" * 60)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = input("\n  API Key de Gemini (Enter para omitir, siempre integrada si se provee): ").strip()
    if api_key:
        print("  Gemini activado — mejorando diagnosticos con IA")
    agente = AgenteAutomotriz(api_key=api_key or None)

    while True:
        print("\n" + "=" * 50)
        print("   [V] NUEVO VEHÍCULO")
        print("=" * 50)
        print("  (Escriba '0' en cualquier campo para volver al menú principal)")

        # --- 1. DATOS DEL VEHÍCULO ---
        print("\n--- DATOS DEL VEHÍCULO ---")
        vin = input("  VIN (opcional): ").strip()
        if vin == "0":
            break
        marca = input("  Marca: ").strip()
        if marca == "0":
            break
        modelo = input("  Modelo: ").strip()
        if modelo == "0":
            break

        try:
            anio_str = input("  Año: ").strip()
            if anio_str == "0":
                break
            anio = int(anio_str) if anio_str else 2020
            km_str = input("  Kilometraje actual (km): ").strip()
            if km_str == "0":
                break
            kilometraje = float(km_str) if km_str else 50000
        except ValueError:
            print("  Valor inválido. Usando valores por defecto.")
            anio, kilometraje = 2020, 50000

        vehiculo = Vehiculo(
            vin=vin or "N/A",
            marca=marca or "No especificada",
            modelo=modelo or "No especificado",
            anio=anio,
            kilometraje=kilometraje,
        )

        # --- 2. SÍNTOMAS ---
        seleccion = mostrar_menu(
            SINTOMAS_DISPONIBLES,
            "--- SELECCIONE LOS SÍNTOMAS (0 para terminar) ---"
        )
        sintomas_seleccionados = [SINTOMAS_DISPONIBLES[s] for s in seleccion]

        if not sintomas_seleccionados:
            print("  Usando ejemplo demostrativo.")
            sintomas_seleccionados = [
                Sintoma("dificultad_arranque", "Dificultad para arrancar"),
                Sintoma("luces_debiles", "Luces débiles"),
            ]

        # --- 3. CÓDIGOS OBD ---
        codigos_seleccionados = []
        resp = input("\n  ¿Desea ingresar códigos OBD-II? (s/n): ").strip().lower()
        if resp == "s":
            seleccion_obd = mostrar_menu(
                CODIGOS_OBD,
                "--- SELECCIONE CÓDIGOS OBD (0 para terminar) ---"
            )
            codigos_seleccionados = [CODIGOS_OBD[o] for o in seleccion_obd]

        # --- 4. PREDICCIONES ---
        print("\n--- PREDICCIÓN DE FALLAS FUTURAS ---")
        predicciones = agente.predecir_fallas(vehiculo)
        if predicciones:
            for nombre, fc, desc in predicciones:
                barra = "#" * int(fc * 20) + "." * (20 - int(fc * 20))
                nom = agente.explicador.DESCRIPCION_FALLAS.get(nombre, nombre)
                print(f"  • {nom:45s} |{barra}| FC={fc:.2f}")
                print(f"    -> {desc}")
        else:
            print("  No se detectan predicciones relevantes.")

        # --- 5. DIAGNÓSTICO ---
        print("\n--- EJECUTANDO DIAGNÓSTICO ---")
        diagnostico = agente.diagnosticar(
            sintomas_seleccionados, codigos_seleccionados, vehiculo
        )

        # --- 6. REPORTE ---
        print()
        print(agente.generar_reporte())

        # --- 7. GUARDAR CASO ---
        if diagnostico.fallas:
            resp = input(
                "\n  ¿Desea guardar este caso para aprendizaje futuro? (s/n): "
            ).strip().lower()
            if resp == "s":
                caso = CasoHistorico(
                    vehiculo_info=vehiculo.descripcion(),
                    sintomas=[s.id for s in sintomas_seleccionados],
                    kilometraje=vehiculo.kilometraje,
                    falla_diagnosticada=diagnostico.fallas[0][0],
                    fc_obtenido=diagnostico.fallas[0][1],
                    accion_realizada=diagnostico.plan_accion[0].descripcion
                    if diagnostico.plan_accion else "N/A",
                    exitoso=True,
                )
                agente.cbr.aprender_caso(caso)
                print("  [OK] Caso guardado exitosamente.")

        # --- 8. CONSUMIR REPUESTO ---
        if diagnostico.fallas:
            resp = input(
                "\n  ¿Desea consumir un repuesto del inventario? (s/n): "
            ).strip().lower()
            if resp == "s":
                falla_id = diagnostico.fallas[0][0]
                if agente.inventario.consumir_repuesto(falla_id):
                    print(f"  [OK] Repuesto consumido para '{falla_id}'.")
                else:
                    print(f"  [NO] No hay stock disponible para '{falla_id}'.")

        # --- 9. CONSUMIR HERRAMIENTA ---
        if diagnostico.fallas:
            resp = input(
                "\n  ¿Necesita usar alguna herramienta del taller? (s/n): "
            ).strip().lower()
            if resp == "s":
                print("\n  Herramientas disponibles:")
                herramientas = agente.inventario.inventario.get("herramientas", {}).get("items", [])
                opciones_h = {}
                for i, h in enumerate(herramientas, 1):
                    estado = "[OK]" if h["stock"] > 0 else "[NO]"
                    print(f"    [{i}] {estado} {h['nombre']} (stock: {h['stock']})")
                    opciones_h[str(i)] = h["nombre"]
                if opciones_h:
                    print("    [0] Cancelar")
                    op_h = input("  Opción: ").strip()
                    if op_h in opciones_h:
                        nombre_h = opciones_h[op_h]
                        if agente.inventario.consumir_herramienta(nombre_h):
                            print(f"  [OK] Herramienta '{nombre_h}' asignada al trabajo.")
                        else:
                            print(f"  [NO] '{nombre_h}' no tiene stock disponible.")

        # --- 10. ¿CONTINUAR? ---
        print("\n" + "-" * 50)
        seguir = input("  ¿Atender otro vehículo? (s/n): ").strip().lower()
        if seguir != "s":
            print("\n  ¡Hasta luego!")
            break


if __name__ == "__main__":
    demo()
