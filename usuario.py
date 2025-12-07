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
        self.satisfaccion = 100

    def entrenar(self, tiempo_total: float):
        """Ciclo principal de entrenamiento siguiendo la rutina."""
        yield from self._preparacion()

        for paso in self.rutina:
            # 1. Comprobación de tiempo límite
            if self.hora_fin > 0 and self.env.now >= self.hora_fin:
                print(f'[{self.env.now:6.2f}] ⌛ {self.nombre}: Se acabó mi tiempo, me voy.')
                break

            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            # 2. Decisiones de perfil (Descanso / Monitor)
            if self.perfil.decidir_descanso():
                yield from self._descanso()

            if self.perfil.decidir_preguntar_monitor():
                yield from self._preguntarAMonitor()

            # 3. BUSCAR MÁQUINA (Sin yield from, es instantáneo)
            maquina = self._buscarMaquinaPorTipo(tipo_maquina)

            if maquina is None:
                # print(f'[{self.env.now:6.2f}] ⚠️ {self.nombre}: No encontré {tipo_maquina} disponible o sin cola.')
                continue

            # 4. INTENTO DE USO (Gestión de Colas)
            print(
                f'[{self.env.now:6.2f}] 🧘 {self.nombre} hace cola en {maquina.nombre} (Esperando a {len(maquina.cola)} personas)')

            # Solicitamos turno en la máquina
            with maquina.resource.request() as peticion:
                yield peticion  # Aquí el proceso se congela hasta que la máquina esté libre

                # Una vez dentro, verificamos si tenemos tiempo para terminar
                if (self.hora_fin > 0) and (self.env.now + duracion_ejercicio > self.hora_fin):
                    print(f'[{self.env.now:6.2f}] ⌛ {self.nombre}: Entré a la máquina pero ya no tengo tiempo.')
                    break

                print(f'[{self.env.now:6.2f}] 💪 {self.nombre} empieza en {maquina.nombre} ({duracion_ejercicio} min)')

                # Realizamos el ejercicio (esto sí toma tiempo)
                yield from maquina.hacer(self, duracion_ejercicio)

                print(f'[{self.env.now:6.2f}] 🏁 {self.nombre} terminó en {maquina.nombre}')

        print(f'[{self.env.now:6.2f}] 👋 {self.nombre}: Rutina finalizada.')

    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        """
        Busca y retorna la mejor máquina disponible (objeto).
        Retorna None si no hay ninguna válida.
        """
        # 1. Filtrar máquinas existentes de ese tipo
        todas = [m for m in self.gimnasio.maquinas if m.tipo_maquina == tipo_deseado]

        if not todas:
            return None

        # 2. Filtrar solo las que funcionan (disponibilidad = True)
        operativas = [m for m in todas if m.disponibilidad]

        if not operativas:
            # Todas rotas
            return None

        # 3. Elegir la que tenga menos cola
        mejor_maquina = min(operativas, key=lambda m: len(m.cola))

        # 4. Filtro de paciencia: Si la cola es inmensa, el usuario desiste
        if len(mejor_maquina.cola) > self.perfil.paciencia_maxima:
            print(f"[{self.env.now:6.2f}] 😤 {self.nombre}: Demasiada cola en {mejor_maquina.nombre}. Paso.")
            return None

        return mejor_maquina

    def _preparacion(self):
        yield self.env.timeout(self.perfil.tiempo_preparacion())
        # print(f'[{self.env.now:6.2f}] 🎒 {self.nombre}: Cosas dejadas en taquilla')

    def _descanso(self):
        duracion = self.perfil.tiempo_descanso()
        # print(f'[{self.env.now:6.2f}] 🥤 {self.nombre}: Descansando {duracion} min')
        yield self.env.timeout(duracion)

    def _preguntarAMonitor(self):
        if not self.gimnasio.monitores: return
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))
        yield from monitor.preguntar(self)

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