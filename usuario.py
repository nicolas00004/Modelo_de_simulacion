import simpy
from Perfil import Perfil
from Problema import Problema
import Ejercicio
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
        self.ocupado = ocupado
        self.hora_fin = hora_fin

        self.satisfaccion = 100

    def entrenar(self, tiempo_total: float):
        """
        Ciclo principal de entrenamiento basado en la rutina del JSON.
        """
        realizados = []
        yield from self._preparacion()

        # Iteramos por los pasos de la rutina del JSON
        for paso in self.rutina:

            # 1. Control del tiempo total límite
            tiempo_restante = tiempo_total - (self.env.now - self.tiempo_llegada)
            # Nota: Ajusté la lógica para restar respecto a la hora de llegada si tiempo_total es duración
            # Si tiempo_total es la hora absoluta de salida, usa: tiempo_total - self.env.now

            if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                print(f'[{self.env.now:.2f}] ⌛ {self.nombre}: Tiempo agotado, me voy a casa.')
                break

            # 2. Extraemos datos del paso actual
            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            # 3. Interrupciones (Descanso / Monitor)
            if self.perfil.decidir_descanso():
                yield from self._descanso()

            if self.perfil.decidir_preguntar_monitor():
                yield from self._preguntarAMonitor()

            # 4. BÚSQUEDA DE MÁQUINA (Corrección del TypeError)
            # Buscamos la máquina específica (SIN yield from, búsqueda instantánea)
            maquina = self._buscarMaquinaPorTipo(tipo_maquina)

            if maquina is None:
                # Si devuelve None es porque están todas rotas o hay demasiada cola
                # print(f'[{self.env.now:.2f}] ⚠️ {self.nombre}: Saltando ejercicio de {tipo_maquina}.')
                continue

            # Verificamos si nos da tiempo a terminar
            if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                print(f'[{self.env.now:.2f}] ⚠️ {self.nombre}: No hay tiempo para {maquina.nombre}, terminando.')
                break

            # 5. USO DE LA MÁQUINA (Gestión de Colas)
            print(
                f'[{self.env.now:.2f}] 🧘 {self.nombre} intenta usar {maquina.nombre} (Cola actual: {len(maquina.cola)})')

            # Solicitamos el recurso (aquí es donde espera si está ocupada)
            with maquina.resource.request() as peticion:
                yield peticion  # ESPERA en la cola

                print(f'[{self.env.now:.2f}] 💪 {self.nombre} empieza en {maquina.nombre} ({duracion_ejercicio} min)')

                # Usamos la máquina (Tiempo de ejercicio)
                # Asumimos que maquina.hacer es un generator (tiene yield)
                yield from maquina.hacer(self, duracion_ejercicio)

                realizados.append(maquina)
                print(f'[{self.env.now:.2f}] 🏁 {self.nombre} terminó en {maquina.nombre}')

        print(f'[{self.env.now:.2f}] 👋 {self.nombre}: Entrenamiento finalizado.')

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        """
        Busca la mejor máquina disponible de un tipo específico.
        Devuelve el OBJETO Maquina o None (no es un generador).
        """
        # 1. Filtramos máquinas que EXISTAN de ese tipo
        todas_maquinas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas_maquinas:
            return None

        # 2. Separamos las OPERATIVAS de las ROTAS
        operativas = [m for m in todas_maquinas if m.disponibilidad]
        rotas = [m for m in todas_maquinas if not m.disponibilidad]

        if not operativas:
            # print(f"[{self.env.now:.2f}] 😡 {self.nombre}: Todas las máquinas de {tipo_deseado} están rotas.")
            return None

        # 3. ELEGIR MÁQUINA (Estrategia: Menos cola)
        mejor_maquina = min(operativas, key=lambda m: len(m.cola))

        # --- DETECCIÓN DE PROBLEMA DE SATURACIÓN ---
        # Si la cola es mayor a su paciencia, se va
        if len(mejor_maquina.cola) > self.perfil.paciencia_maxima:
            print(
                f"[{self.env.now:.2f}] 😤 {self.nombre}: Demasiada cola en {mejor_maquina.nombre} ({len(mejor_maquina.cola)}). Me salto el ejercicio.")
            return None

        return mejor_maquina

    def _preparacion(self):
        yield self.env.timeout(self.perfil.tiempo_preparacion())
        # print(f'{self.env.now:.2f}: {self.nombre} cosas dejadas en taquilla')

    def _descanso(self):
        duracion_descanso = self.perfil.tiempo_descanso()
        # print(f'{self.env.now:.2f}: {self.nombre} descansando {duracion_descanso} minutos')
        yield self.env.timeout(duracion_descanso)

    def _preguntarAMonitor(self):
        """
        Busca al monitor con menos cola y espera su turno
        """
        if not self.gimnasio.monitores:
            return

        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))
        yield from monitor.preguntar(self)

    # --- MÉTODO LEGACY (Opcional, se mantiene por compatibilidad) ---
    def _buscarEjercicio(self, realizados: list):
        # Este método era para comportamiento aleatorio.
        # No se usa en la lógica de Rutinas JSON actual.
        return None

    @classmethod
    def generar_desde_json(cls, ruta_archivo, env, gimnasio):
        """
        Carga usuarios completos con Rutina, Perfil y Problema.
        """
        usuarios_generados = []

        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            for item in datos:
                datos_perfil = item.get('perfil')
                # Creamos perfil, asegurando que tenga kwargs para evitar errores
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

            print(f"✅ Se han cargado {len(usuarios_generados)} usuarios desde {ruta_archivo}")
            return usuarios_generados

        except FileNotFoundError:
            print(f"❌ Error: No se encontró el archivo {ruta_archivo}")
            return []
        except Exception as e:
            print(f"❌ Error inesperado cargando usuarios: {e}")
            return []