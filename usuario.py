import simpy
import random
from Perfil import Perfil
from Problema import Problema


class Usuario:
    def __init__(self, env: simpy.Environment, gimnasio,
                 id_usuario: int, nombre: str, tipo_usuario: str, tiempo_llegada: float,
                 rutina: list, perfil: Perfil, problema: Problema,
                 config: dict,
                 subtipo: str = "Estudiante", plan_pago: str = "Mensual",
                 hora_fin: float = 0, faltas_consecutivas: int = 0):

        # Referencias
        self.env = env
        self.gimnasio = gimnasio
        self.config = config

        # Identidad (Ahora usamos nombres reales como "Ana García")
        self.id = id_usuario
        self.nombre = nombre
        self.tipo_usuario = tipo_usuario  # "Socio" o "Pase_Diario"
        self.subtipo = subtipo
        self.plan_pago = plan_pago

        # Planificación y Estado
        self.tiempo_llegada = tiempo_llegada
        self.rutina = rutina
        self.perfil = perfil
        self.problema = problema
        self.hora_fin = hora_fin
        self.satisfaccion = 100
        self.faltas_consecutivas = faltas_consecutivas

        # Control de Sesión
        self.logger_sesion = None
        self.dia_sesion = None
        self.numero_sesion = None
        self.process = None

    def _notificar(self, mensaje, emoji, tipo_evento, datos_extra=None):
        """Alinea nombres y envía el texto limpio tanto a consola como al .txt de sesión."""
        tiempo_sim = f"[{self.env.now:7.2f}]"

        # .ljust(20) asegura que la columna de nombres sea uniforme
        mensaje_limpio = f"{tiempo_sim} {emoji} {self.nombre.ljust(20)} {mensaje}"

        # 1. Mostrar en la consola del IDE
        print(mensaje_limpio)

        # 2. Guardar en el archivo .txt (sin prefijos de hora real ni INFO)
        if self.logger_sesion:
            self.logger_sesion.log(mensaje_limpio)

        # 3. Registrar datos técnicos en el CSV
        self._log_evento(mensaje, tipo_evento, datos_extra)

    def _log_evento(self, mensaje, tipo_evento, datos_extra=None):
        """Captura el estado económico y de mantenimiento para el CSV."""
        if self.logger_sesion:
            if datos_extra is None: datos_extra = {}

            balance_actual = getattr(self.gimnasio, 'balance', 0)
            num_rotas = self.gimnasio.contar_maquinas_rotas()

            datos_completos = {
                "tiempo_simulacion": f"{self.env.now:.2f}",
                "tipo_evento": tipo_evento,
                "id_usuario": self.id,
                "nombre": self.nombre,
                "dia": self.dia_sesion,
                "sesion": self.numero_sesion,
                "satisfaccion_actual": self.satisfaccion,
                "balance_economico": balance_actual,
                "maquinas_rotas_count": num_rotas,
                **datos_extra
            }
            self.logger_sesion.registrar_datos(datos_completos)

    def _actualizar_satisfaccion(self, cambio):
        """Modifica el humor del socio dentro del rango [0-100]."""
        self.satisfaccion = max(0, min(100, self.satisfaccion + cambio))

    def entrenar(self, tiempo_total_maximo: float):
        """Lógica central de SimPy: El usuario recorre su rutina."""
        PARAMS = self.config["satisfaccion"]
        pen_salida = PARAMS.get("penalizacion_salida_forzada", 5)
        pen_rota = PARAMS.get("penalizacion_maquina_rota", 10)

        try:
            self._notificar("entra al gimnasio", "🚪", "INICIO", {"satisfaccion_inicio": self.satisfaccion})
            yield from self._preparacion()

            for paso in self.rutina:
                # 1. Comprobar tiempo personal
                if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                    self._actualizar_satisfaccion(-pen_salida)
                    self._notificar("se va por falta de tiempo personal.", "⌛", "SALIDA_FORZADA")
                    return

                tipo_maq = paso['tipo_maquina_deseada']
                duracion_ejercicio = paso['tiempo_uso']

                # Comportamientos aleatorios
                if self.perfil.decidir_descanso(): yield from self._descanso()

                maquina = self._buscarMaquinaPorTipo(tipo_maq)
                if maquina is None: continue

                # Gestión de colas
                cola_i = len(maquina.cola)
                emoji_cola = "🧘" if cola_i > 0 else "🏃"
                self._notificar(f"en {maquina.nombre} (cola: {cola_i})", emoji_cola, "ESPERA_COLA")

                with maquina.resource.request() as peticion:
                    t_llegada = self.env.now
                    yield peticion  # Esperar turno

                    # Penalización por espera
                    t_espera = self.env.now - t_llegada
                    limite = PARAMS.get("minutos_paciencia_cola", 5)
                    if t_espera > limite:
                        enfado = int((t_espera - limite) * PARAMS.get("penalizacion_espera_cola", 1.0))
                        self._actualizar_satisfaccion(-enfado)
                        if enfado > 0:
                            self._notificar(f"se queja por la espera ({t_espera:.1f}m)", "😡", "QUEJA")

                    # Uso de la máquina
                    self._notificar(f"usa {maquina.nombre} ({duracion_ejercicio}m)", "💪", "USO_MAQUINA")
                    try:
                        yield from maquina.hacer(self, duracion_ejercicio)
                    except Exception as e:
                        if isinstance(e, simpy.Interrupt): raise e

                        # Si la máquina explota
                        self._actualizar_satisfaccion(-pen_rota)
                        self.gimnasio.registrar_reparacion()  # Descuenta dinero del gym
                        self._notificar(f"¡{maquina.nombre} SE ROMPIÓ!", "💥", "MAQUINA_ROTA")
                        continue

            self._notificar("termina su rutina y se va.", "👋", "SALIDA")

        except simpy.Interrupt as i:
            if i.cause == "FIN_SESION":
                self._actualizar_satisfaccion(-5)
                self._notificar("¡EXPULSADO POR CIERRE DE SESIÓN!", "🚨", "SALIDA_CIERRE")

    def _buscarMaquinaPorTipo(self, tipo):
        """Busca máquinas operativas y elige la mejor (menos cola)."""
        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo]
        operativas = [m for m in todas if m.disponibilidad]

        if not operativas:
            self._actualizar_satisfaccion(-self.config["satisfaccion"].get("penalizacion_sin_maquina", 2))
            self._notificar(f"no encuentra {tipo} operativa", "❌", "FALLO_MAQUINA")
            return None

        mejor = min(operativas, key=lambda m: len(m.cola))
        if len(mejor.cola) > self.perfil.paciencia_maxima:
            self._notificar(f"pasa de usar {mejor.nombre} por demasiada cola", "😤", "ABANDONO_COLA")
            return None
        return mejor

    def _preparacion(self):
        yield self.env.timeout(self.perfil.tiempo_preparacion())

    def _descanso(self):
        self._notificar("descansa un poco...", "🥤", "DESCANSO")
        yield self.env.timeout(self.perfil.tiempo_descanso())

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores: return
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))
        self._notificar(f"pide consejo a {monitor.nombre}", "🗣️", "CONSULTA")
        yield from monitor.preguntar(self)