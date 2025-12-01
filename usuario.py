import simpy
from ejercicio import Ejercicio

class Usuario:
    def __init__(self, env: simpy.Environment, hora_fin: float, perfil: Perfil):
        self.env = env
        self.hora_fin = hora_fin
        self.perfil = perfil

    def entrenar(self):
        realizados = []
        yield from self._preparacion()

        while True:
            tiempo_restante = self.hora_fin - self.env.now
            ejercicio = self._buscarEjercicio(realizados)

            if tiempo_restante < ejercicio.tiempo():
                break

            if self.rand.random() < self.perfil.probabilidad_descanso:
                yield from self._descanso()
            if self.rand.random() < .05:
                yield from self._preguntarAMonitor()
            
            print(f'{self.env.now}: Iniciando ejercicio {ejercicio}')
            ejercicio.hacer()
            print(f'{self.env.now}: Terminando ejercicio {ejercicio}')
            realizados.append(ejercicio)

        print(f'{self.env.now}: Entrenamiento finalizado')

    def _preparacion(self):
        yield self.env.timeout(5)
        print(f'{self.env.now}: Cosas dejadas en taquilla')

    def _descanso(self):
        duracion_descanso = self.perfil.tiempo_descanso()
        print(f'{self.env.now}: Descansando {duracion_descanso} minutos')
        yield self.env.timeout(duracion_descanso)

    def _buscarEjercicio(self, realizados: list[Ejercicio]):
        """
        saca un ejercicio aleatorio segun el perfil del usuario comprobando si no lo ha hecho ya
        ve si la maquina esta rota (busca otro)
        ve si la maquina esta libre (o espera o busca otro)
        lo devuelve
        """
        return Ejercicio()

    def _preguntarAMonitor(self):
        """
        busca al monitor con menos cola y espera su turno
        """