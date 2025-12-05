
import simpy
from collections import deque
class Cola:
    def __init__(self, env: simpy.Environment, capacidad: int, tipo_cola: str,Cola:deque):
        self.env = env
        self.capacidad = capacidad
        self.Cola = Cola
        self.tipo_cola = tipo_cola.upper()
        if self.tipo_cola == "FIFO":
            self.recurso = simpy.Resource(env, capacity=capacidad)

        elif self.tipo_cola == "PRIORIDAD":
            self.recurso = simpy.PriorityResource(env, capacity=capacidad)

        else:
            raise ValueError(f"Tipo de cola '{tipo_cola}' no reconocido. Usa 'FIFO' o 'PRIORIDAD'")


    def obtener_ocupacion(self):
        """Devuelve cuántas máquinas están siendo usadas actualmente."""
        return self.recurso.count

    def obtener_gente_en_espera(self):
        """Devuelve cuánta gente hay esperando en la cola."""
        return len(self.recurso.queue)

    def esta_lleno(self):
        """Devuelve True si todas las máquinas están ocupadas."""
        return self.recurso.count >= self.capacidad

    def porcentaje_ocupacion(self):
        return (self.recurso.count / self.capacidad) * 100