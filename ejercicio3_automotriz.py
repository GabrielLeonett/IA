"""
Agente Cognitivo para Diagnóstico y Mantenimiento Predictivo Automotriz
Ejercicio Práctico 3 - Sistema de Razonamiento Basado en Reglas + FC + CBR

Arquitectura BDI:
  - Creencias: Base de Conocimiento (reglas, ontología, casos históricos)
  - Deseos: Seguridad > Efectividad > Eficiencia
  - Intenciones: Percepcion -> Filtro -> Razonamiento -> Planificacion -> Actuacion
"""

import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


# =============================================================================
# CLASES DE LA ONTOLOGÍA (Creencias)
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
class Falla:
    id: str
    nombre: str
    descripcion: str
    sistema_afectado: str
    fc: float = 0.0


@dataclass
class AccionMantenimiento:
    descripcion: str
    costo_estimado: float = 0.0
    tiempo_estimado_horas: float = 0.0


@dataclass
class Diagnostico:
    fallas: list[tuple[str, float]]  # (nombre_falla, fc)
    urgencia: str  # Rojo, Amarillo, Verde
    plan_accion: list[AccionMantenimiento]
    explicacion: str


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
# BASE DE CONOCIMIENTO
# =============================================================================

class BaseConocimiento:
    def __init__(self):
        self.reglas: list[Regla] = []
        self._cargar_reglas()

    def _cargar_reglas(self):
        self.reglas = [
            # === SISTEMA ELÉCTRICO ===
            Regla(
                {"dificultad_arranque": True, "luces_debiles": True},
                "bateria_descargada", 0.85,
                "Dificultad de arranque junto con luces débiles es altamente "
                "sugestivo de batería descargada. La batería no tiene carga "
                "suficiente para alimentar el motor de arranque ni los sistemas auxiliares."
            ),
            Regla(
                {"dificultad_arranque": True, "testigo_bateria": True},
                "bateria_descargada", 0.80,
                "El testigo de batería encendido durante el arranque indica "
                "que el sistema eléctrico no está recibiendo voltaje adecuado."
            ),
            Regla(
                {"ruido_chirrido": True, "luces_debiles": True},
                "alternador_danado", 0.80,
                "Ruido chirriante proveniente del alternador junto con luces "
                "débiles indica que el alternador no está generando la carga suficiente."
            ),
            Regla(
                {"testigo_bateria": True, "luces_debiles": True},
                "alternador_danado", 0.75,
                "Testigo de batería + luces débiles mientras el motor está en "
                "marcha sugiere falla en el alternador."
            ),
            # === SISTEMA DE ENCENDIDO ===
            Regla(
                {"testigo_motor": True, "tirones_aceleracion": True},
                "bujia_deteriorada", 0.70,
                "Testigo del motor encendido con tirones al acelerar indica "
                "fallo de encendido en uno o más cilindros por bujías desgastadas."
            ),
            Regla(
                {"perdida_potencia": True, "humo_negro_escape": True},
                "filtro_aire_tapado", 0.75,
                "Pérdida de potencia con humo negro indica mezcla rica por "
                "restricción en la entrada de aire (filtro tapado)."
            ),
            # === SISTEMA MECÁNICO ===
            Regla(
                {"vibracion": True, "ruido_metalico": True},
                "correa_distribucion_desgastada", 0.80,
                "Vibración anormal con ruido metálico del motor sugiere "
                "desgaste en la correa de distribución o sus tensores."
            ),
            Regla(
                {"humo_negro_escape": True, "olor_gasolina": True},
                "inyector_sucio", 0.70,
                "Humo negro con olor a gasolina sin quemar indica mala "
                "atomización del combustible por inyectores sucios."
            ),
            # === SISTEMA DE FRENOS ===
            Regla(
                {"freno_blando": True, "ruido_frenado": True},
                "freno_desgastado", 0.85,
                "Pedal de freno blando acompañado de ruido metálico al frenar "
                "indica desgaste crítico de las pastillas o discos de freno."
            ),
            # === SISTEMA DE REFRIGERACIÓN ===
            Regla(
                {"sobrecalentamiento": True, "perdida_refrigerante": True},
                "termostato_danado", 0.75,
                "Sobrecalentamiento con pérdida de refrigerante sugiere "
                "termostato atascado en posición cerrada o fuga en el sistema."
            ),
            # === SISTEMA DE COMBUSTIBLE ===
            Regla(
                {"testigo_motor": True, "consumo_excesivo": True},
                "sonda_lambda_danada", 0.70,
                "Testigo del motor con consumo excesivo de combustible indica "
                "lectura incorrecta de la sonda lambda (mezcla aire-combustible)."
            ),
            Regla(
                {"perdida_potencia": True, "testigo_motor": True},
                "valvula_egr_tapada", 0.65,
                "Pérdida de potencia con testigo del motor puede indicar "
                "la válvula EGR obstruida por carbonilla."
            ),
            # === SISTEMA DE DIRECCIÓN ===
            Regla(
                {"direccion_dura": True, "ruido_direccion": True},
                "bomba_direccion_danada", 0.75,
                "Dirección dura con ruido (gemido) al girar indica baja presión "
                "en la bomba de dirección asistida."
            ),
            # === CÓDIGOS OBD-II ===
            Regla(
                {"codigo_P0562": True},
                "bateria_descargada", 0.90,
                "Código OBD P0562: System Voltage Low. Confirma que el voltaje "
                "del sistema eléctrico está por debajo del umbral mínimo."
            ),
            Regla(
                {"codigo_P0300": True},
                "bujia_deteriorada", 0.85,
                "Código OBD P0300: Random Misfire Detectado. Fallo de encendido "
                "aleatorio en múltiples cilindros."
            ),
            Regla(
                {"codigo_P0171": True},
                "sonda_lambda_danada", 0.80,
                "Código OBD P0171: System Too Lean. Mezcla aire-combustible "
                "demasiado pobre por fallo en sonda lambda."
            ),
            Regla(
                {"codigo_P0420": True},
                "catalizador_danado", 0.85,
                "Código OBD P0420: Catalyst Efficiency Below Threshold. "
                "El catalizador no está funcionando a la eficiencia requerida."
            ),
            Regla(
                {"codigo_P0401": True},
                "valvula_egr_tapada", 0.80,
                "Código OBD P0401: EGR Flow Insufficient. Flujo insuficiente "
                "en el sistema de recirculación de gases de escape."
            ),
            # === REGLA DE MANTENIMIENTO PREDICTIVO ===
            Regla(
                {"kilometraje_alto": True, "ultimo_cambio_aceite": True},
                "cambio_aceite_proximo", 0.70,
                "El vehículo tiene alto kilometraje desde el último cambio "
                "de aceite. Se recomienda programar cambio preventivo."
            ),
        ]

    def obtener_reglas_por_conclusion(self, conclusion: str) -> list[Regla]:
        return [r for r in self.reglas if r.conclusion == conclusion]

    def todas_conclusiones(self) -> set[str]:
        return {r.conclusion for r in self.reglas}


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
        reglas_activadas: list[Regla] = []

        for regla in bc.reglas:
            fc_resultado = regla.evaluar(hechos)
            if fc_resultado is not None and abs(fc_resultado) >= 0.2:
                if regla.conclusion not in conclusiones:
                    conclusiones[regla.conclusion] = []
                conclusiones[regla.conclusion].append(fc_resultado)
                reglas_activadas.append(regla)

        fc_final: dict[str, float] = {}
        for conclusion, fcs in conclusiones.items():
            if not fcs:
                continue
            fc_total = fcs[0]
            positivos = [f for f in fcs if f > 0]
            negativos = [f for f in fcs if f < 0]

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
    fecha: datetime = field(default_factory=datetime.now)


class GestorCasosCBR:
    def __init__(self, archivo: str = None):
        self.casos: list[CasoHistorico] = []
        if archivo:
            self.cargar(archivo)
        else:
            self._cargar_casos_ejemplo()

    def _cargar_casos_ejemplo(self):
        self.casos = [
            CasoHistorico("Ford Focus 2019", ["dificultad_arranque", "luces_debiles"],
                          85000, "bateria_descargada", 0.92, "Reemplazo de batería", True),
            CasoHistorico("Chevrolet Onix 2020", ["testigo_motor", "tirones_aceleracion"],
                          62000, "bujia_deteriorada", 0.78, "Cambio de bujías", True),
            CasoHistorico("Volkswagen Gol 2018", ["freno_blando", "ruido_frenado"],
                          110000, "freno_desgastado", 0.88, "Reemplazo pastillas + discos", True),
            CasoHistorico("Toyota Corolla 2021", ["testigo_motor", "consumo_excesivo"],
                          45000, "sonda_lambda_danada", 0.72, "Reemplazo sonda lambda", True),
            CasoHistorico("Fiat Cronos 2017", ["ruido_chirrido", "luces_debiles"],
                          95000, "alternador_danado", 0.81, "Reconstrucción alternador", False),
            CasoHistorico("Renault Sandero 2020", ["perdida_potencia", "humo_negro_escape"],
                          78000, "filtro_aire_tapado", 0.76, "Cambio filtro de aire", True),
        ]

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

    def guardar(self, archivo: str):
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump([c.__dict__ for c in self.casos], f, default=str, indent=2)

    def cargar(self, archivo: str):
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        self.casos = [CasoHistorico(**d) for d in datos]


# =============================================================================
# EXPLICADOR
# =============================================================================

class Explicador:
    DESCRIPCION_FALLAS = {
        "bateria_descargada": "Batería descargada o en fin de vida útil",
        "alternador_danado": "Alternador dañado o con regulador de voltaje defectuoso",
        "bujia_deteriorada": "Bujías desgastadas o en mal estado",
        "filtro_aire_tapado": "Filtro de aire obstruido que restringe el flujo de aire",
        "correa_distribucion_desgastada": "Correa de distribución desgastada o con tensión incorrecta",
        "inyector_sucio": "Inyectores de combustible sucios u obstruidos",
        "freno_desgastado": "Pastillas o discos de freno desgastados",
        "termostato_danado": "Termostato del sistema de refrigeración defectuoso",
        "sonda_lambda_danada": "Sensor de oxígeno (sonda lambda) con lectura incorrecta",
        "valvula_egr_tapada": "Válvula EGR obstruida por depósitos de carbonilla",
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
        "bujia_deteriorada": "Verde",
        "filtro_aire_tapado": "Verde",
        "inyector_sucio": "Verde",
        "sonda_lambda_danada": "Verde",
        "valvula_egr_tapada": "Verde",
        "catalizador_danado": "Verde",
        "cambio_aceite_proximo": "Verde",
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
            AccionMantenimiento("Inspeccionar estado de bujías (color, desgaste, electrodo)", 0, 0.5),
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
            urgencia = self.URGENCIA_FALLAS.get(falla, "Verde")
            if urgencia == "Rojo":
                return "Rojo"
        for falla in fallas:
            urgencia = self.URGENCIA_FALLAS.get(falla, "Verde")
            if urgencia == "Amarillo":
                return "Amarillo"
        return "Verde"

    def generar_explicacion(self, fallas: dict, reglas_activadas: list[Regla]) -> str:
        if not fallas:
            return "No se pudo determinar una falla con suficiente certeza."

        principal = list(fallas.items())[0]
        partes = [
            f"=== DIAGNÓSTICO AUTOMOTRIZ ===",
            f"",
            f"Falla principal detectada: {self.DESCRIPCION_FALLAS.get(principal[0], principal[0])}",
            f"Nivel de certeza (FC): {principal[1]:.1%}",
            f"",
        ]

        urgencia = self.obtener_urgencia(fallas)
        etiqueta_urgencia = {
            "Rojo": "[ROJO] URGENCIA ROJA: Atencion inmediata requerida (< 1 hora)",
            "Amarillo": "[AMARILLO] URGENCIA AMARILLA: Reparar en menos de 24 horas",
            "Verde": "[VERDE] URGENCIA VERDE: Mantenimiento programable",
        }
        partes.append(etiqueta_urgencia.get(urgencia, ""))
        partes.append("")

        partes.append("--- Reglas activadas para el diagnóstico ---")
        for falla_nombre, _ in list(fallas.items())[:3]:
            reglas_falla = [r for r in reglas_activadas if r.conclusion == falla_nombre]
            for r in reglas_falla:
                condiciones_str = ", ".join(
                    f"{k}={v}" for k, v in r.condiciones.items()
                )
                partes.append(f"  * SI [{condiciones_str}] -> {falla_nombre} FC={r.fc}")
            partes.append("")

        if len(fallas) > 1:
            partes.append("--- Otras fallas consideradas ---")
            for nombre, fc in list(fallas.items())[1:4]:
                desc = self.DESCRIPCION_FALLAS.get(nombre, nombre)
                partes.append(f"  • {desc} (FC={fc:.1%})")

        return "\n".join(partes)

    def obtener_plan(self, fallas: dict) -> list[AccionMantenimiento]:
        acciones: list[AccionMantenimiento] = []
        vistos: set = set()
        for falla in fallas:
            plan = self.PLANES_ACCION.get(falla, [])
            for accion in plan:
                if accion.descripcion not in vistos:
                    acciones.append(accion)
                    vistos.add(accion.descripcion)
        return acciones


# =============================================================================
# AGENTE AUTOMOTRIZ (Núcleo BDI)
# =============================================================================

class AgenteAutomotriz:
    def __init__(self):
        self.bc = BaseConocimiento()
        self.motor = MotorInferencia()
        self.cbr = GestorCasosCBR()
        self.explicador = Explicador()
        self.ultimas_reglas_activadas: list[Regla] = []
        self.ultimo_diagnostico: Optional[Diagnostico] = None

    def diagnosticar(
        self,
        sintomas: list[Sintoma],
        codigos_obd: list[CodigoOBD] | None = None,
        vehiculo: Vehiculo | None = None
    ) -> Diagnostico:
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
        fallas_filtradas = {
            k: v for k, v in fallas_fc.items() if abs(v) >= umbral
        }

        # Ajuste con CBR
        sintomas_presentes = {s.id for s in sintomas if s.presente}
        for falla in list(fallas_filtradas.keys()):
            fallas_filtradas[falla] = self.cbr.ajustar_fc_con_cbr(
                falla, fallas_filtradas[falla], sintomas_presentes
            )

        fallas_ordenadas = dict(
            sorted(fallas_filtradas.items(), key=lambda x: -x[1])
        )

        urgencia = self.explicador.obtener_urgencia(fallas_ordenadas)
        plan = self.explicador.obtener_plan(fallas_ordenadas)
        explicacion = self.explicador.generar_explicacion(
            fallas_ordenadas, self.ultimas_reglas_activadas
        )

        self.ultimo_diagnostico = Diagnostico(
            fallas=list(fallas_ordenadas.items()),
            urgencia=urgencia,
            plan_accion=plan,
            explicacion=explicacion,
        )
        return self.ultimo_diagnostico

    def predecir_fallas(self, vehiculo: Vehiculo) -> list[tuple[str, float, str]]:
        predicciones: list[tuple[str, float, str]] = []

        if vehiculo.kilometraje > 80000:
            predicciones.append((
                "correa_distribucion_desgastada",
                0.6 + min(0.005 * (vehiculo.kilometraje - 80000) / 1000, 0.3),
                f"Correa de distribución cercana al cambio recomendado cada 80.000-100.000 km."
            ))

        if vehiculo.anio <= datetime.now().year - 5:
            predicciones.append((
                "bateria_descargada",
                0.5 + min(0.1 * (datetime.now().year - vehiculo.anio - 5), 0.4),
                f"Batería con más de 5 años. Se recomienda reemplazo preventivo."
            ))

        if vehiculo.kilometraje > 60000:
            predicciones.append((
                "bujia_deteriorada",
                0.5,
                f"Bujías con alto kilometraje. Se recomienda inspección y reemplazo."
            ))

        if vehiculo.kilometraje > 50000:
            predicciones.append((
                "cambio_aceite_proximo",
                0.75,
                f"Verificar intervalo de cambio de aceite según manual del fabricante."
            ))

        return predicciones

    def generar_reporte(self) -> str:
        if not self.ultimo_diagnostico:
            return "No hay diagnóstico previo."

        d = self.ultimo_diagnostico
        lineas = [
            "=" * 60,
            "   REPORTE DE DIAGNÓSTICO - AGENTE AUTOMOTRIZ COGNITIVO",
            "=" * 60,
            f"",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Urgencia: {d.urgencia}",
            f"",
            f"--- Fallas Detectadas ---",
        ]

        for nombre, fc in d.fallas:
            desc = self.explicador.DESCRIPCION_FALLAS.get(nombre, nombre)
            barra = "█" * int(abs(fc) * 20) + "░" * (20 - int(abs(fc) * 20))
            lineas.append(f"  {desc:40s} |{barra}| FC={fc:+.2f}")

        lineas.extend([
            f"",
            f"--- Plan de Acción Sugerido ---",
        ])
        costo_total = 0.0
        tiempo_total = 0.0
        for i, accion in enumerate(d.plan_accion, 1):
            lineas.append(
                f"  {i}. {accion.descripcion} "
                f"(${accion.costo_estimado:,.0f}, {accion.tiempo_estimado_horas:.1f}h)"
            )
            costo_total += accion.costo_estimado
            tiempo_total += accion.tiempo_estimado_horas

        lineas.extend([
            f"",
            f"  Costo total estimado: ${costo_total:,.0f}",
            f"  Tiempo total estimado: {tiempo_total:.1f} horas",
            f"",
            d.explicacion,
        ])
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
    "P0562": CodigoOBD("P0562", "System Voltage Low - Bajo voltaje en sistema eléctrico"),
    "P0300": CodigoOBD("P0300", "Random Misfire - Fallo de encendido aleatorio"),
    "P0171": CodigoOBD("P0171", "System Too Lean - Mezcla pobre"),
    "P0420": CodigoOBD("P0420", "Catalyst Efficiency - Eficiencia del catalizador baja"),
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
        if multi and op == "0":
            break
        if op in opciones:
            seleccionadas.append(op)
            if not multi:
                break
        else:
            print("  Opción inválida.")
            if not multi:
                break
    return seleccionadas


def demo():
    print()
    print("=" * 60)
    print("   AGENTE COGNITIVO PARA DIAGNÓSTICO AUTOMOTRIZ")
    print("   Ejercicio Práctico 3 - Sistema Basado en Reglas + FC + CBR")
    print("=" * 60)

    agente = AgenteAutomotriz()

    # --- 1. DATOS DEL VEHÍCULO ---
    print("\n--- DATOS DEL VEHÍCULO ---")
    vehiculo = Vehiculo(
        vin=input("  VIN (opcional): ").strip() or "N/A",
        marca=input("  Marca: ").strip() or "No especificada",
        modelo=input("  Modelo: ").strip() or "No especificado",
        anio=int(input("  Año: ").strip() or 2020),
        kilometraje=float(input("  Kilometraje actual (km): ").strip() or 50000),
    )

    # --- 2. SELECCIÓN DE SÍNTOMAS ---
    seleccion = mostrar_menu(SINTOMAS_DISPONIBLES, "--- SELECCIONE LOS SÍNTOMAS (una o varias) ---")
    sintomas_seleccionados = [SINTOMAS_DISPONIBLES[s] for s in seleccion]

    if not sintomas_seleccionados:
        print("  No se ingresaron síntomas. Usando ejemplo demostrativo.")
        sintomas_seleccionados = [
            Sintoma("dificultad_arranque", "Dificultad para arrancar"),
            Sintoma("luces_debiles", "Luces débiles"),
        ]

    # --- 3. CÓDIGOS OBD (OPCIONAL) ---
    print("\n¿Desea ingresar códigos OBD-II? (s/n)")
    if input("  ").strip().lower() == "s":
        seleccion_obd = mostrar_menu(CODIGOS_OBD, "--- SELECCIONE CÓDIGOS OBD ---")
        codigos_seleccionados = [CODIGOS_OBD[o] for o in seleccion_obd]
    else:
        codigos_seleccionados = []

    # --- 4. PREDICCIÓN DE FALLAS FUTURAS ---
    print("\n--- PREDICCIÓN DE FALLAS FUTURAS (Mantenimiento Predictivo) ---")
    predicciones = agente.predecir_fallas(vehiculo)
    if predicciones:
        for nombre, fc, desc in predicciones:
            barra = "█" * int(fc * 20) + "░" * (20 - int(fc * 20))
            nom = agente.explicador.DESCRIPCION_FALLAS.get(nombre, nombre)
            print(f"  • {nom:45s} |{barra}| FC={fc:.2f}")
            print(f"    -> {desc}")
    else:
        print("  No se detectan predicciones relevantes.")

    # --- 5. DIAGNÓSTICO ---
    print("\n--- EJECUTANDO DIAGNÓSTICO ---")
    diagnostico = agente.diagnosticar(sintomas_seleccionados, codigos_seleccionados, vehiculo)

    # --- 6. REPORTE FINAL ---
    print()
    print(agente.generar_reporte())
    print()
    print("=" * 60)

    print("\n¿Desea guardar este caso para aprendizaje futuro (CBR)? (s/n)")
    if input("  ").strip().lower() == "s":
        caso = CasoHistorico(
            vehiculo_info=vehiculo.descripcion(),
            sintomas=[s.id for s in sintomas_seleccionados],
            kilometraje=vehiculo.kilometraje,
            falla_diagnosticada=diagnostico.fallas[0][0] if diagnostico.fallas else "desconocida",
            fc_obtenido=diagnostico.fallas[0][1] if diagnostico.fallas else 0.0,
            accion_realizada=diagnostico.plan_accion[0].descripcion if diagnostico.plan_accion else "N/A",
            exitoso=True,
        )
        agente.cbr.aprender_caso(caso)
        print("  Caso guardado exitosamente.")

    input("\nPresione Enter para finalizar...")


if __name__ == "__main__":
    demo()
