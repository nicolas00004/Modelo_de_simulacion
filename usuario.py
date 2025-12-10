import simpy
from Perfil import Perfil
from Problema import Problema
import json

# Intentamos importar la excepción, si no existe creamos una dummy
try:
    from Maquina import MachineBrokenError
except ImportError:
    class MachineBrokenError(Exception):
        pass


class Usuario:
    def __init__(self, env: simpy.Environment, gimnasio,
                 id_usuario: int, nombre: str, tipo_usuario: str, tiempo_llegada: float,
                 rutina: list, perfil: Perfil, problema: Problema,
                 ocupado: bool = False, hora_fin: float = 0, faltas_consecutivas: int = 0):

        self.env = env
        self.gimnasio = gimnasio
        self.id = id_usuario
        self.nombre = nombre
        self.tipo_usuario = tipo_usuario
        self.tiempo_llegada = tiempo_llegada
        self.rutina = rutina
        self.perfil = perfil
        self.problema = problema
        self.hora_fin = hora_fin
        self.faltas_consecutivas = faltas_consecutivas

        self.satisfaccion = 100

        # Logging
        self.logger_sesion = None
        self.dia_sesion = None
        self.numero_sesion = None
        self.process = None

    def _notificar(self, mensaje, emoji, tipo_evento, datos_extra=None):
        """
        Muestra por consola y guarda en log.
        """
        # 1. Consola (Visual)
        tiempo_sim = f"[{self.env.now:6.2f}]"
        print(f"{tiempo_sim} {emoji} {self.nombre} {mensaje}")

        # 2. Archivo (Técnico)
        self._log_evento(f"{emoji} {mensaje}", tipo_evento, datos_extra)

    def _log_evento(self, mensaje, tipo_evento, datos_extra=None):
        if self.logger_sesion:
            if datos_extra is None: datos_extra = {}

            # Log Texto
            self.logger_sesion.log(f"[{self.nombre}] {mensaje}", tipo_evento)

            # Log CSV
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
        """Ciclo principal de entrenamiento."""

        self._notificar(f"entra al gimnasio (Meta: {tiempo_total}m)", "🚪", "INICIO",
                        {"duracion": tiempo_total, "satisfaccion_inicio": self.satisfaccion})

        yield from self._preparacion()

        paso_num = 0
        for paso in self.rutina:
            paso_num += 1

            # 1. Chequeo de tiempo
            if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                # Penalización suave por irse antes
                self._actualizar_satisfaccion(-2)
                self._notificar("se va porque se le acabó el tiempo.", "⌛", "SALIDA_FORZADA")
                break

            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            # 2. Decisiones previas
            if self.perfil.decidir_descanso(): yield from self._descanso()
            if self.perfil.decidir_preguntar_monitor(): yield from self._preguntarAMonitor()

            # 3. Buscar máquina
            maquina = self._buscarMaquinaPorTipo(tipo_maquina)
            if maquina is None: continue

            # 4. PROCESO DE MÁQUINA (COLA + USO)
            cola_actual = len(maquina.cola)

            if cola_actual > 0:
                msg_cola = f"hace cola en {maquina.nombre} (Esperando a {cola_actual} personas)"
                emoji_cola = "🧘"
            else:
                msg_cola = f"va directo a {maquina.nombre} (Libre)"
                emoji_cola = "🏃"

            self._notificar(msg_cola, emoji_cola, "ESPERA_COLA",
                            {"maquina": maquina.nombre, "cola_tamano": cola_actual})

            try:
                with maquina.resource.request() as peticion:
                    tiempo_espera_inicio = self.env.now
                    yield peticion

                    tiempo_espera_real = self.env.now - tiempo_espera_inicio

                    # --- LÓGICA DE PACIENCIA SUAVIZADA ---
                    # Antes: >2 min, -1 punto por min.
                    # Ahora: >4 min, -0.5 puntos por min.
                    if tiempo_espera_real > 4:
                        penalizacion = int((tiempo_espera_real - 4) * 0.5)
                        if penalizacion > 0:
                            self._actualizar_satisfaccion(-penalizacion)
                            print(f"   ⚠️ {self.nombre} ha esperado {tiempo_espera_real:.1f} min (Sat -{penalizacion})")

                    # Chequeo de tiempo post-cola
                    if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                        self._actualizar_satisfaccion(-3)  # Antes -10
                        self._notificar(f"deja {maquina.nombre} sin usar (no le da tiempo)", "🏃💨", "ABANDONO_MAQUINA")
                        break

                    self._notificar(f"empieza en {maquina.nombre} ({duracion_ejercicio} min)", "💪", "USO_MAQUINA",
                                    {"maquina": maquina.nombre, "duracion": duracion_ejercicio})

                    try:
                        yield from maquina.hacer(self, duracion_ejercicio)
                        self._log_evento(f"Libera {maquina.nombre}", "FIN_MAQUINA", {"maquina": maquina.nombre})

                    except Exception as e:
                        # Rotura de máquina: Antes -20, Ahora -10
                        self._actualizar_satisfaccion(-10)
                        self._notificar(f"¡La máquina {maquina.nombre} SE ROMPIÓ!", "💥", "MAQUINA_ROTA")
                        continue

            except Exception as e:
                print(f"Error inesperado con {self.nombre}: {e}")

        self._notificar("termina su rutina y se va a casa.", "👋", "SALIDA")

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas:
            self._actualizar_satisfaccion(-1)  # Antes -5
            self._log_evento(f"No hay máquinas tipo {tipo_deseado}", "ERROR_MAQUINA")
            return None

        operativas = [m for m in todas if m.disponibilidad]
        if not operativas:
            self._actualizar_satisfaccion(-2)  # Antes -10
            self._notificar(f"ve que todas las {tipo_deseado} están rotas", "🔧", "MAQUINAS_ROTAS")
            return None

        mejor_maquina = min(operativas, key=lambda m: len(m.cola))
        cola_mejor = len(mejor_maquina.cola)

        if cola_mejor > self.perfil.paciencia_maxima:
            self._actualizar_satisfaccion(-3)  # Antes -15
            self._notificar(f"ve mucha cola ({cola_mejor}) en {mejor_maquina.nombre} y pasa.", "😤", "ABANDONO_POR_COLA")
            return None

        return mejor_maquina

    def _preparacion(self):
        tiempo = self.perfil.tiempo_preparacion()
        self._log_evento(f"Vestuario ({tiempo}m)", "VESTUARIO")
        yield self.env.timeout(tiempo)

    def _descanso(self):
        tiempo = self.perfil.tiempo_descanso()
        self._notificar(f"descansa {tiempo} min para recuperar aliento.", "🥤", "DESCANSO")
        yield self.env.timeout(tiempo)

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores: return
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))

        # Penalización monitor ocupado: Antes -2, Ahora -0 (son pacientes)
        # if len(monitor.cola) > 2: self._actualizar_satisfaccion(-1)

        self._notificar(f"espera al monitor {monitor.nombre}...", "🗣️", "CONSULTA_MONITOR")
        yield from monitor.preguntar(self)