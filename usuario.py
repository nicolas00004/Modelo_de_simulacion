import simpy
import Perfil
import Gimnasio
import Problema
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
        realizados = []
        yield from self._preparacion()

        #  iteramos por los pasos de la rutina del JSON
        for paso in self.rutina:

            # Control del tiempo total límite (si se acaba el tiempo, se va a casa)
            tiempo_restante = tiempo_total - self.env.now
            if tiempo_restante <= 0:
                print(f'{self.env.now}: Tiempo agotado, abandonando rutina.')
                break

            # Extraemos datos del paso actual del JSON
            tipo_maquina = paso['tipo_maquina_deseada']
            duracion_ejercicio = paso['tiempo_uso']

            # --- INTERRUPCIONES (Descanso / Monitor) ---
            # Mantenemos tu lógica de perfil
            if self.perfil.decidir_descanso():
                yield from self._descanso()

            if self.perfil.decidir_preguntar_monitor():
                yield from self._preguntarAMonitor()


            # Buscamos la máquina específica en lugar de una aleatoria

            ejercicio = yield from self._buscarMaquinaPorTipo(tipo_maquina)

            if ejercicio is None:
                print(f'{self.env.now}: No se encontró máquina de tipo {tipo_maquina}, saltando ejercicio.')
                continue

            # Verificamos si nos da tiempo a terminar este ejercicio específico
            if tiempo_restante < duracion_ejercicio:
                print(f'{self.env.now}: No hay tiempo suficiente para {ejercicio}, terminando.')
                break

            print(f'{self.env.now}: Iniciando ejercicio en {ejercicio.nombre} ({duracion_ejercicio} min)')

            # Asumimos que 'hacer' ahora acepta la duración impuesta por la rutina
            yield from ejercicio.hacer(self, duracion_ejercicio)

            realizados.append(ejercicio)
            print(f'{self.env.now}: Terminando ejercicio en {ejercicio.nombre}')

        print(f'{self.env.now}: Entrenamiento finalizado')


    def _buscarMaquinaPorTipo(self, tipo_deseado: str):
        while True:
            candidatas = [m for m in self.gimnasio.maquinas
                          if m.tipo_maquina == tipo_deseado and m.disponibilidad]

            if not candidatas:
                # Si no hay ninguna máquina de ese tipo (todas rotas o no existen), salimos
                return None

            # Elegimos la que tenga menos cola (Estrategia inteligente)
            # Si tu clase Maquina no tiene atributo 'cola', usa: random.choice(candidatas)
            ejercicio = min(candidatas, key=lambda m: len(m.cola) if hasattr(m, 'cola') else 0)

            # Lógica de espera si está muy llena (similar a tu original)
            # Si la cola es aceptable para el perfil, la elegimos
            if len(ejercicio.cola) <= self.perfil.paciencia_maxima:  # Suponiendo que tengas este atributo
                return ejercicio

            # Si hay mucha cola, esperamos un poco antes de volver a mirar (tiempo de búsqueda)
            yield self.env.timeout(self.perfil.tiempo_busqueda_maquina())

    def _preparacion(self):
        yield self.env.timeout(self.perfil.tiempo_preparacion())
        print(f'{self.env.now}: Cosas dejadas en taquilla')

    def _descanso(self):
        duracion_descanso = self.perfil.tiempo_descanso()
        print(f'{self.env.now}: Descansando {duracion_descanso} minutos')
        yield self.env.timeout(duracion_descanso)

    def _buscarEjercicio(self, realizados: list[Ejercicio]):
        while 1:
            ejercicio = self.gimnasio.ejercicio_aleatorio(self.perfil)

            if not (ejercicio in realizados or ejercicio.averiado() or ejercicio.cola or len(ejercicio.usando) > 1):
                if ejercicio.usando == 1 and not ejercicio.usando[0].perfil.probabilidad_compartir_maquina(self.perfil):
                    # la probabilidad de compartir maquina depende del perfil del que la esta usando y del tuyo
                    ejercicio.encolar(self)
                break
            yield self.env.timeout(self.perfil.tiempo_busqueda_maquina())

        return ejercicio

    def _preguntarAMonitor(self):
        """
        busca al monitor con menos cola y espera su turno
        """
        monitor = min(self.gimnasio.monitores, key=lambda m: len(m.cola))
        yield from monitor.preguntar(self)

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

            print(f" Se han cargado {len(usuarios_generados)} usuarios desde {ruta_archivo}")
            return usuarios_generados

        except FileNotFoundError:
            print(f" Error: No se encontró el archivo {ruta_archivo}")
            return []
        except KeyError as e:
            print(f" Error de Datos: Falta el campo obligatorio {e} en el JSON.")
            return []
        except Exception as e:
            print(f" Error inesperado: {e}")
            return []