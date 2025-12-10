import simpy
from Perfil import Perfil
from Problema import Problema
import json


class Usuario:
    def __init__(self, env: simpy.Environment, gimnasio,
                 id_usuario: int, nombre: str, tipo_usuario: str, tiempo_llegada: float,
                 rutina: list, perfil: Perfil, problema: Problema,
                 ocupado: bool = False, hora_fin: float = 0):

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

        # Satisfacción inicial al 100%
        self.satisfaccion = 100

        # Atributos para logging (se inyectan desde main.py)
        self.logger_sesion = None
        self.dia_sesion = None
        self.numero_sesion = None

    def _log_evento(self, mensaje, tipo_evento, datos_extra=None):
        """Registra un evento en el log de la sesión si está disponible"""
        if self.logger_sesion:
            # Log en formato texto
            self.logger_sesion.log(f"[{self.nombre}] {mensaje}", tipo_evento)

            # Log en CSV con datos estructurados
            if datos_extra is None:
                datos_extra = {}

            datos_completos = {
                "tiempo_simulacion": f"{self.env.now:.2f}",
                "tipo_evento": tipo_evento,
                "id_usuario": self.id,
                "nombre": self.nombre,
                "dia": self.dia_sesion,
                "sesion": self.numero_sesion,
                "satisfaccion_actual": self.satisfaccion,  # Añadimos esto para trackear la felicidad
                **datos_extra
            }
            self.logger_sesion.registrar_datos(datos_completos)

    def entrenar(self, tiempo_total: float):
        """Ciclo principal de entrenamiento siguiendo la rutina."""
        self._log_evento(
            f"Inicia entrenamiento (duración planificada: {tiempo_total:.1f} min, perfil: {self.perfil.tipo})",
            "INICIO_ENTRENAMIENTO",
            {"duracion_planificada": tiempo_total, "perfil": self.perfil.tipo, "pasos_rutina": len(self.rutina)}
        )

        yield from self._preparacion()

        paso_num = 0
        for paso in self.rutina:
            paso_num += 1

            # 1. Comprobación de tiempo límite
            if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                print(f'[{self.env.now:6.2f}] ⌛ {self.nombre}: Se acabó mi tiempo, me voy.')

                # Penalización pequeña por no acabar la rutina
                self._actualizar_satisfaccion(-5)

                self._log_evento(
                    f"Tiempo límite alcanzado. Sale del gimnasio (paso {paso_num}/{len(self.rutina)})",
                    "TIEMPO_AGOTADO",
                    {"paso_completado": paso_num - 1, "total_pasos": len(self.rutina)}
                )
                break

            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            self._log_evento(
                f"Paso {paso_num}/{len(self.rutina)}: Busca {tipo_maquina} por {duracion_ejercicio} min",
                "PASO_RUTINA",
                {"paso": paso_num, "tipo_maquina": tipo_maquina, "duracion": duracion_ejercicio}
            )

            # 2. Decisiones de perfil (Descanso / Monitor)
            if self.perfil.decidir_descanso():
                yield from self._descanso()

            if self.perfil.decidir_preguntar_monitor():
                yield from self._preguntarAMonitor()

            # 3. BUSCAR MÁQUINA (Sin yield from, es instantáneo)
            maquina = self._buscarMaquinaPorTipo(tipo_maquina)

            if maquina is None:
                # Si no encuentra máquina (porque desistió por cola o no hay), pasa al siguiente
                self._log_evento(
                    f"No encuentra máquina tipo {tipo_maquina} disponible. Salta paso {paso_num}",
                    "MAQUINA_NO_DISPONIBLE",
                    {"tipo_buscado": tipo_maquina, "paso": paso_num}
                )
                continue

            # 4. INTENTO DE USO (Gestión de Colas)
            cola_actual = len(maquina.cola)
            print(
                f'[{self.env.now:6.2f}] 🧘 {self.nombre} hace cola en {maquina.nombre} (Esperando a {cola_actual} personas)')

            self._log_evento(
                f"Entra en cola de {maquina.nombre} (personas esperando: {cola_actual})",
                "ESPERA_COLA",
                {"maquina": maquina.nombre, "cola": cola_actual, "tipo_maquina": tipo_maquina}
            )

            # Solicitamos turno en la máquina
            with maquina.resource.request() as peticion:
                tiempo_espera_inicio = self.env.now
                yield peticion  # Se congela aquí esperando turno
                tiempo_espera_real = self.env.now - tiempo_espera_inicio

                # --- LÓGICA DE SATISFACCIÓN POR ESPERA ---
                # Si espera más de 2 minutos, empieza a enfadarse (1 punto por minuto extra)
                if tiempo_espera_real > 2:
                    penalizacion = int(tiempo_espera_real - 2)
                    self._actualizar_satisfaccion(-penalizacion)
                # -----------------------------------------

                self._log_evento(
                    f"Accede a {maquina.nombre} (esperó {tiempo_espera_real:.1f} min)",
                    "ACCESO_MAQUINA",
                    {"maquina": maquina.nombre, "tiempo_espera": f"{tiempo_espera_real:.2f}"}
                )

                # Verificar si tras la espera aún tiene tiempo
                if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                    print(f'[{self.env.now:6.2f}] ⌛ {self.nombre}: Entré a la máquina pero ya no tengo tiempo.')
                    self._actualizar_satisfaccion(-10)  # Penalización por frustración

                    self._log_evento(
                        f"Abandona {maquina.nombre} sin usarla (sin tiempo)",
                        "ABANDONA_MAQUINA",
                        {"maquina": maquina.nombre, "razon": "sin_tiempo"}
                    )
                    break

                print(f'[{self.env.now:6.2f}] 💪 {self.nombre} empieza en {maquina.nombre} ({duracion_ejercicio} min)')
                self._log_evento(
                    f"Comienza ejercicio en {maquina.nombre} ({duracion_ejercicio} min)",
                    "USAR_MAQUINA",
                    {"maquina": maquina.nombre, "duracion": duracion_ejercicio, "tipo_maquina": tipo_maquina}
                )

                # Realizamos el ejercicio
                yield from maquina.hacer(self, duracion_ejercicio)

                print(f'[{self.env.now:6.2f}] 🏁 {self.nombre} terminó en {maquina.nombre}')
                self._log_evento(
                    f"Termina ejercicio en {maquina.nombre}",
                    "FIN_MAQUINA",
                    {"maquina": maquina.nombre, "tipo_maquina": tipo_maquina}
                )

        print(f'[{self.env.now:6.2f}] 👋 {self.nombre}: Rutina finalizada.')
        self._log_evento(
            f"Finaliza rutina completa (pasos completados: {paso_num}/{len(self.rutina)})",
            "FIN_ENTRENAMIENTO",
            {"pasos_completados": paso_num, "total_pasos": len(self.rutina),
             "tiempo_total": f"{self.env.now - self.tiempo_llegada:.2f}"}
        )

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        """
        Busca y retorna la mejor máquina disponible (objeto).
        Retorna None si no hay ninguna válida o la cola es excesiva.
        """
        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas:
            # Penalización grave: no existe la máquina que necesita
            self._actualizar_satisfaccion(-5)
            self._log_evento(
                f"No existen máquinas tipo {tipo_deseado} en el gimnasio",
                "BUSCAR_MAQUINA",
                {"tipo_buscado": tipo_deseado, "resultado": "no_existe"}
            )
            return None

        operativas = [m for m in todas if m.disponibilidad]

        if not operativas:
            # Penalización grave: todas rotas
            self._actualizar_satisfaccion(-10)
            self._log_evento(
                f"Todas las máquinas {tipo_deseado} están fuera de servicio",
                "BUSCAR_MAQUINA",
                {"tipo_buscado": tipo_deseado, "total": len(todas), "resultado": "todas_rotas"}
            )
            return None

        # Elegir la que tenga menos cola
        mejor_maquina = min(operativas, key=lambda m: len(m.cola))
        cola_mejor = len(mejor_maquina.cola)

        # 4. Filtro de paciencia: Si la cola es inmensa, el usuario desiste
        # El atributo .paciencia_maxima viene del perfil (clase PerfilGenerado o JSON)
        if cola_mejor > self.perfil.paciencia_maxima:
            print(f"[{self.env.now:6.2f}] 😤 {self.nombre}: Demasiada cola en {mejor_maquina.nombre}. Paso.")

            # --- PENALIZACIÓN POR FRUSTRACIÓN ---
            self._actualizar_satisfaccion(-15)
            # ------------------------------------

            self._log_evento(
                f"Desiste de {mejor_maquina.nombre} (cola {cola_mejor} > paciencia {self.perfil.paciencia_maxima})",
                "ABANDONA_COLA",
                {"maquina": mejor_maquina.nombre, "cola": cola_mejor, "paciencia_maxima": self.perfil.paciencia_maxima}
            )
            return None

        self._log_evento(
            f"Encuentra {mejor_maquina.nombre} (cola: {cola_mejor})",
            "MAQUINA_ENCONTRADA",
            {"maquina": mejor_maquina.nombre, "tipo_maquina": tipo_deseado, "cola": cola_mejor,
             "operativas": len(operativas)}
        )

        return mejor_maquina

    def _actualizar_satisfaccion(self, cambio):
        """Método auxiliar para modificar la satisfacción sin bajar de 0."""
        self.satisfaccion += cambio
        if self.satisfaccion < 0:
            self.satisfaccion = 0
        elif self.satisfaccion > 100:
            self.satisfaccion = 100

    def _preparacion(self):
        tiempo_prep = self.perfil.tiempo_preparacion()
        self._log_evento(
            f"Entra al vestuario ({tiempo_prep} min)",
            "VESTUARIO_ENTRADA",
            {"tiempo_vestuario": tiempo_prep}
        )
        yield self.env.timeout(tiempo_prep)
        self._log_evento("Sale del vestuario", "VESTUARIO_SALIDA")

    def _descanso(self):
        duracion = self.perfil.tiempo_descanso()
        print(f'[{self.env.now:6.2f}] 🥤 {self.nombre}: Descansando {duracion} min')
        self._log_evento(
            f"Toma descanso ({duracion} min)",
            "DESCANSO",
            {"tiempo_descanso": duracion}
        )
        yield self.env.timeout(duracion)
        self._log_evento("Finaliza descanso", "FIN_DESCANSO")

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores:
            self._log_evento("Quiere preguntar a monitor pero no hay disponibles", "MONITOR_NO_DISPONIBLE")
            return

        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))

        # Si hay mucha cola en el monitor, también penalizamos un poco
        if len(monitor.cola) > 2:
            self._actualizar_satisfaccion(-2)

        self._log_evento(
            f"Solicita ayuda del monitor (cola: {len(monitor.cola)})",
            "SOLICITAR_MONITOR",
            {"monitor": monitor.nombre if hasattr(monitor, 'nombre') else "Monitor", "cola": len(monitor.cola)}
        )
        yield from monitor.preguntar(self)
        self._log_evento("Termina consulta con monitor", "FIN_MONITOR")

    @classmethod
    def generar_desde_json(cls, ruta_archivo, env, gimnasio):
        usuarios_generados = []
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            for item in datos:
                datos_perfil = item.get('perfil')
                obj_perfil = Perfil(**datos_perfil) if datos_perfil else None

                datos_problema = item.get('problema')
                obj_problema = Problema(**datos_problema) if datos_problema else None

                nuevo_usuario = cls(
                    env=env,
                    gimnasio=gimnasio,
                    id_usuario=item['id'],
                    nombre=item['nombre'],
                    tipo_usuario=item['tipo_usuario'],
                    tiempo_llegada=item['tiempo_llegada'],
                    rutina=item['rutina'],
                    perfil=obj_perfil,
                    problema=obj_problema,
                    ocupado=item.get('ocupado', False),
                    hora_fin=item.get('hora_fin', 0)
                )
                usuarios_generados.append(nuevo_usuario)

            print(f"✅ Cargados {len(usuarios_generados)} usuarios.")
            return usuarios_generados

        except Exception as e:
            print(f"❌ Error cargando usuarios: {e}")
            return []