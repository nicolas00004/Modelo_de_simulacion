import simpy
import random
import Problema
import Tipo_Cola


class Monitor:
    def __init__(self, env: simpy.Environment, nombre_monitor: str, id_monitor: int, cola_Monitor: Tipo_Cola,
                 problema_monitor: Problema,disponibilidad:bool):
        self.env = env
        self.nombre_monitor = nombre_monitor
        self.id_monitor = id_monitor
        self.cola_Monitor = cola_Monitor
        self.problema_monitor = problema_monitor
        self.disponibilidad = disponibilidad


    def atender(self, usuario):
        if(self.disponibilidad):
            print(f"[{self.env.now:.2f}]  {self.nombre_monitor}: Hola {usuario.nombre}, voy a resolver tu problema.")
            tiempo_atencion = self.problema_monitor.tiempo_solucion
            yield self.env.timeout(tiempo_atencion)
            print(f"[{self.env.now:.2f}]  {self.nombre_monitor}: Problema resuelto para {usuario.nombre}.")
        else:
            self.cola_Monitor.Cola.add(usuario)

