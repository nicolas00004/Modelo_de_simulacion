import simpy
import random
from Perfil import Perfil
from Problema import Problema
import json

try:
    from Maquina import MachineBrokenError
except ImportError:
    class MachineBrokenError(Exception):
        pass


class Usuario:
    def __init__(self, env: simpy.Environment, gimnasio,
                 id_usuario: int, nombre: str, tipo_usuario: str, tiempo_llegada: float,
                 rutina: list, perfil: Perfil, problema: Problema,
                 config: dict,
                 subtipo: str = "Estudiante", plan_pago: str = "Mensual",  # Nuevos campos
                 ocupado: bool = False, hora_fin: float = 0, faltas_consecutivas: int = 0):

        self.env = env
        self.gimnasio = gimnasio
        self.id = id_usuario
        self.nombre = nombre
        self.tipo_usuario = tipo_usuario
        self.subtipo = subtipo
        self.plan_pago = plan_pago
        self.tiempo_llegada = tiempo_llegada
        self.rutina = rutina
        self.perfil = perfil
        self.problema = problema
        self.config = config
        self.hora_fin = hora_fin
        self.faltas_consecutivas = faltas_consecutivas

        self.satisfaccion = 100

        self.logger_sesion = None
        self.dia_sesion = None
        self.numero_sesion = None
        self.process = None

    def _notificar(self, mensaje, emoji, tipo_evento, datos_extra=None):
        tiempo_sim = f"[{self.env.now:6.2f}]"
        print(f"{tiempo_sim} {emoji} {self.nombre} {mensaje}")
        self._log_evento(f"{emoji} {mensaje}", tipo_evento, datos_extra)

    def _log_evento(self, mensaje, tipo_evento, datos_extra=None):
        if self.logger_sesion:
            if datos_extra is None: datos_extra = {}
            self.logger_sesion.log(f"[{self.nombre}] {mensaje}", tipo_evento)
            datos_completos = {
                "tiempo_simulacion": f"{self.env.now:.2f}",
                "tipo_evento": tipo_evento,
                "id_usuario": self.id,
                "nombre": self.nombre,
                "dia": self.dia_sesion,
                "sesion": self.numero_sesion,
                "satisfaccion_actual": self.satisfaccion,
                **datos_extra
            }
            self.logger_sesion.registrar_datos(datos_completos)

    def _actualizar_satisfaccion(self, cambio):
        self.satisfaccion += cambio
        if self.satisfaccion < 0:
            self.satisfaccion = 0
        elif self.satisfaccion > 100:
            self.satisfaccion = 100

    def entrenar(self, tiempo_total: float):
        PARAMS = self.config["satisfaccion"]
        pen_salida = PARAMS.get("penalizacion_salida_forzada", 2)
        pen_rota = PARAMS.get("penalizacion_maquina_rota", 5)

        # --- BLOQUE TRY PARA CAPTURAR LA EXPULSIÓN DE SESIÓN ---
        try:
            self._notificar(f"entra al gimnasio (Meta: {tiempo_total}m)", "🚪", "INICIO",
                            {"duracion": tiempo_total, "satisfaccion_inicio": self.satisfaccion})

            yield from self._preparacion()

            for paso in self.rutina:
                # 1. TIEMPO INDIVIDUAL AGOTADO
                if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                    self._actualizar_satisfaccion(-pen_salida)
                    self._notificar("se va por tiempo personal.", "⌛", "SALIDA_FORZADA")
                    return  # Salimos de la función

                tipo_maquina = paso['tipo_maquina_deseada']
                duracion_ejercicio = paso['tiempo_uso']

                if self.perfil.decidir_descanso(): yield from self._descanso()
                if self.perfil.decidir_preguntar_monitor(): yield from self._preguntarAMonitor()

                maquina = self._buscarMaquinaPorTipo(tipo_maquina)
                if maquina is None: continue

                # Gestión de Cola
                cola_actual = len(maquina.cola)
                if cola_actual > 0:
                    self._notificar(f"hace cola en {maquina.nombre} ({cola_actual} pax)", "🧘", "ESPERA_COLA",
                                    {"maquina": maquina.nombre, "cola_tamano": cola_actual})
                else:
                    self._notificar(f"va directo a {maquina.nombre}", "🏃", "ESPERA_COLA",
                                    {"maquina": maquina.nombre, "cola_tamano": 0})

                try:
                    with maquina.resource.request() as peticion:
                        t_inicio = self.env.now
                        yield peticion  # Aquí se bloquea esperando (o es interrumpido)

                        t_espera = self.env.now - t_inicio

                        # Lógica de paciencia
                        limite = PARAMS.get("minutos_paciencia_cola", 2)
                        tasa = PARAMS.get("penalizacion_espera_cola", 2.0)

                        if t_espera > limite:
                            penalizacion = int((t_espera - limite) * tasa)
                            if penalizacion > 0:
                                self._actualizar_satisfaccion(-penalizacion)
                                print(f"      😡 {self.nombre} odia esperar: {t_espera:.1f}m (Sat -{penalizacion})")

                        # Chequeo post-cola
                        if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                            self._actualizar_satisfaccion(-pen_salida)
                            self._notificar(f"deja {maquina.nombre} sin usar (no time)", "🏃💨", "ABANDONO_MAQUINA")
                            break

                        self._notificar(f"empieza en {maquina.nombre} ({duracion_ejercicio}m)", "💪", "USO_MAQUINA",
                                        {"maquina": maquina.nombre, "duracion": duracion_ejercicio})

                        try:
                            # Aquí se bloquea haciendo ejercicio (o es interrumpido)
                            yield from maquina.hacer(self, duracion_ejercicio)
                            self._log_evento(f"Libera {maquina.nombre}", "FIN_MAQUINA", {"maquina": maquina.nombre})

                        except Exception as e:
                            # Si es interrupción de SimPy, la relanzamos para que la capture el bloque externo
                            if isinstance(e, simpy.Interrupt): raise e

                            # Si es rotura de máquina
                            self._actualizar_satisfaccion(-pen_rota)
                            self._notificar(f"¡{maquina.nombre} SE ROMPIÓ!", "💥", "MAQUINA_ROTA")
                            continue

                except simpy.Interrupt as i:
                    # Capturamos interrupción MIENTRAS esperamos cola o usamos máquina
                    raise i  # Relanzamos para salir del bucle for

            self._notificar("termina rutina y se va.", "👋", "SALIDA")

        except simpy.Interrupt as i:
            # --- AQUÍ SE GESTIONA LA SALIDA FORZADA POR CIERRE DE SESIÓN ---
            if i.cause == "FIN_SESION":
                self._actualizar_satisfaccion(-5)  # Pequeña molestia por echarle
                self._notificar("¡FIN DE SESIÓN! Es expulsado del gimnasio.", "🚨", "SALIDA_CIERRE")
            else:
                print(f"Interrupción desconocida para {self.nombre}: {i.cause}")

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        PARAMS = self.config["satisfaccion"]
        pen_sin_maq = PARAMS.get("penalizacion_sin_maquina", 1)

        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas:
            self._actualizar_satisfaccion(-pen_sin_maq)
            self._log_evento(f"No hay máquinas tipo {tipo_deseado}", "ERROR_MAQUINA")
            return None

        operativas = [m for m in todas if m.disponibilidad]
        if not operativas:
            self._actualizar_satisfaccion(-pen_sin_maq)
            self._notificar(f"ve todas las {tipo_deseado} rotas", "🔧", "MAQUINAS_ROTAS")
            return None

        mejor_maquina = min(operativas, key=lambda m: len(m.cola))
        cola_mejor = len(mejor_maquina.cola)

        if cola_mejor > self.perfil.paciencia_maxima:
            self._actualizar_satisfaccion(-pen_sin_maq)
            self._notificar(f"ve mucha cola ({cola_mejor}) en {mejor_maquina.nombre} y pasa.", "😤", "ABANDONO_POR_COLA")
            return None

        return mejor_maquina

    def _preparacion(self):
        yield self.env.timeout(self.perfil.tiempo_preparacion())

    def _descanso(self):
        self._notificar(f"descansa un poco...", "🥤", "DESCANSO")
        yield self.env.timeout(self.perfil.tiempo_descanso())

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores: return
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))
        self._notificar(f"pregunta a {monitor.nombre}...", "🗣️", "CONSULTA_MONITOR")
        yield from monitor.preguntar(self)