import simpy
from ejercicio import Ejercicio

class Usuario():
    def __init__(self, env: simpy.Environment, hora_fin: float, perfil: Perfil, gimnasio: Gimnasio):
        self.env = env
        self.perfil = perfil
        self.gimnasio = gimnasio

    def entrenar(self, tiempo_total: float):
        realizados = []
        yield from self._preparacion()

        while True:
            tiempo_restante = tiempo_total - self.env.now

            if self.perfil.decidir_descanso():
                yield from self._descanso()
            if self.perfil.decidir_preguntar_monitor():
                yield from self._preguntarAMonitor()
            

            # devuelve 0 o 1 segun: self.rand.random() < self.perfil.probabilidad_descanso():
            if self.perfil.decidir_descanso():
                yield self._descanso()
            # self.rand.random() < self.perfil.probabilidad_monitor()
            if self.perfil.decidir_preguntar_monitor():
                yield self._preguntarAMonitor()
            
            ejercicio = yield from self._buscarEjercicio(realizados)
            
            if tiempo_restante < ejercicio.tiempo:
                break

            ejercicio = yield from self._buscarEjercicio(realizados)
            print(f'{self.env.now}: Iniciando ejercicio {ejercicio}')
            yield from ejercicio.hacer(self)
            realizados.append(ejercicio)
            print(f'{self.env.now}: Terminando ejercicio {ejercicio}')

        print(f'{self.env.now}: Entrenamiento finalizado')

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