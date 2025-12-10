import simpy
from Perfil import Perfil
from Problema import Problema
import json

# Intentamos importar la excepción de la máquina, si falla creamos una dummy
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

        # Satisfacción inicial
        self.satisfaccion = 100

        # Atributos para logging (se inyectan desde main.py)
        self.logger_sesion = None
        self.dia_sesion = None
        self.numero_sesion = None
        self.process = None  # Para poder interrumpirlo si la máquina se rompe

    def _log_evento(self, mensaje, tipo_evento, datos_extra=None):
        """
        Registra un evento. ASEGURA QUE LA SATISFACCIÓN SIEMPRE SE GUARDE EN EL CSV.
        """
        if self.logger_sesion:
            # 1. Log en formato texto (.log)
            self.logger_sesion.log(f"[{self.nombre}] {mensaje}", tipo_evento)

            # 2. Log en CSV (.csv)
            if datos_extra is None:
                datos_extra = {}

            datos_completos = {
                "tiempo_simulacion": f"{self.env.now:.2f}",
                "tipo_evento": tipo_evento,
                "id_usuario": self.id,
                "nombre": self.nombre,
                "dia": self.dia_sesion,
                "sesion": self.numero_sesion,
                "satisfaccion_actual": self.satisfaccion,  # CAMPO CLAVE
                **datos_extra
            }
            self.logger_sesion.registrar_datos(datos_completos)

    def _actualizar_satisfaccion(self, cambio):
        """Modifica la satisfacción manteniéndola entre 0 y 100."""
        self.satisfaccion += cambio
        if self.satisfaccion < 0:
            self.satisfaccion = 0
        elif self.satisfaccion > 100:
            self.satisfaccion = 100

    def entrenar(self, tiempo_total: float):
        """Ciclo principal de entrenamiento."""

        self._log_evento(
            f"Inicia rutina (Duración: {tiempo_total}m - Sat: {self.satisfaccion})",
            "INICIO",
            {"duracion": tiempo_total, "satisfaccion_inicio": self.satisfaccion}
        )

        yield from self._preparacion()

        paso_num = 0
        for paso in self.rutina:
            paso_num += 1

            # 1. Verificar tiempo límite de sesión
            if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                self._actualizar_satisfaccion(-5)
                self._log_evento("Se acaba el tiempo de sesión. Se va.", "SALIDA_FORZADA")
                break

            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            # 2. Decisiones previas (Descanso / Monitor)
            if self.perfil.decidir_descanso(): yield from self._descanso()
            if self.perfil.decidir_preguntar_monitor(): yield from self._preguntarAMonitor()

            # 3. BUSCAR MÁQUINA (CRÍTICO: HACER ESTO ANTES DE USARLA)
            maquina = self._buscarMaquinaPorTipo(tipo_maquina)

            if maquina is None:
                # Si no hay máquina o la cola es muy larga, _buscarMaquinaPorTipo ya bajó la satisfacción
                continue

            # 4. GESTIÓN DE COLA Y USO
            cola_actual = len(maquina.cola)

            # Registramos que entramos en cola (con la satisfacción actual)
            self._log_evento(
                f"Entra en cola de {maquina.nombre} ({cola_actual} pax)",
                "ESPERA_COLA",
                {
                    "maquina": maquina.nombre,
                    "cola_tamano": cola_actual,
                    "satisfaccion_actual": self.satisfaccion
                }
            )

            # TRY/EXCEPT GENERAL PARA CAPTURAR CUALQUIER FALLO
            try:
                with maquina.resource.request() as peticion:
                    tiempo_espera_inicio = self.env.now
                    yield peticion  # Aquí nos bloqueamos esperando turno

                    # Al despertar, calculamos cuánto esperamos
                    tiempo_espera_real = self.env.now - tiempo_espera_inicio

                    # Penalización por espera excesiva
                    if tiempo_espera_real > 2:
                        penalizacion = int(tiempo_espera_real - 2)
                        self._actualizar_satisfaccion(-penalizacion)

                    self._log_evento(
                        f"Consigue {maquina.nombre} tras {tiempo_espera_real:.1f}m espera",
                        "ACCESO_MAQUINA",
                        {
                            "maquina": maquina.nombre,
                            "duracion": f"{tiempo_espera_real:.2f}",
                            "satisfaccion_actual": self.satisfaccion
                        }
                    )

                    # Verificar si al conseguir la máquina aún nos queda tiempo
                    if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                        self._actualizar_satisfaccion(-10)  # Frustración alta
                        self._log_evento("Deja la máquina sin usar (sin tiempo)", "ABANDONO_MAQUINA")
                        break

                    # USAR MÁQUINA
                    self._log_evento(f"Usando {maquina.nombre}", "USO_MAQUINA", {"duracion": duracion_ejercicio})

                    try:
                        # Aquí es donde la máquina puede romperse
                        yield from maquina.hacer(self, duracion_ejercicio)
                        self._log_evento(f"Libera {maquina.nombre}", "FIN_MAQUINA")

                    except Exception as e:
                        # CAPTURA DE ROTURA DE MÁQUINA
                        # print(f"💥 {self.nombre}: La máquina {maquina.nombre} falló.")
                        self._actualizar_satisfaccion(-20)  # Gran enfado
                        self._log_evento(
                            f"¡Máquina {maquina.nombre} se ROMPIÓ durante el uso!",
                            "MAQUINA_ROTA",
                            {"satisfaccion_actual": self.satisfaccion}
                        )
                        continue  # Salta al siguiente ejercicio

            except Exception as e:
                print(f"Error inesperado procesando a {self.nombre}: {e}")

        self._log_evento("Fin del entrenamiento. Se va a casa.", "SALIDA")

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas:
            self._actualizar_satisfaccion(-5)
            self._log_evento(f"No hay máquinas tipo {tipo_deseado}", "ERROR_MAQUINA")
            return None

        operativas = [m for m in todas if m.disponibilidad]
        if not operativas:
            self._actualizar_satisfaccion(-10)
            self._log_evento(f"Todas las máquinas {tipo_deseado} rotas", "MAQUINAS_ROTAS")
            return None

        # Elegimos la que tenga menos cola
        mejor_maquina = min(operativas, key=lambda m: len(m.cola))
        cola_mejor = len(mejor_maquina.cola)

        # Filtro de paciencia
        if cola_mejor > self.perfil.paciencia_maxima:
            self._actualizar_satisfaccion(-15)
            self._log_evento(
                f"Abandona {mejor_maquina.nombre} (Cola {cola_mejor} > Paciencia)",
                "ABANDONO_POR_COLA",
                {"satisfaccion_actual": self.satisfaccion}
            )
            return None

        return mejor_maquina

    def _preparacion(self):
        tiempo = self.perfil.tiempo_preparacion()
        self._log_evento(f"Vestuario ({tiempo}m)", "VESTUARIO")
        yield self.env.timeout(tiempo)

    def _descanso(self):
        tiempo = self.perfil.tiempo_descanso()
        self._log_evento(f"Descanso ({tiempo}m)", "DESCANSO")
        yield self.env.timeout(tiempo)

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores: return
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))

        if len(monitor.cola) > 2:
            self._actualizar_satisfaccion(-2)

        self._log_evento(f"Pregunta a monitor (Cola {len(monitor.cola)})", "CONSULTA_MONITOR")
        yield from monitor.preguntar(self)