import simpy


class GestorCola:
    def __init__(self, env: simpy.Environment, capacidad: int, tipo_cola: str = "FIFO"):
        self.env = env
        self.capacidad = capacidad
        self.tipo_cola = tipo_cola.upper()

        # Validamos los tipos soportados
        tipos_validos = ["FIFO", "LIFO", "PRIORIDAD", "SJF"]
        if self.tipo_cola not in tipos_validos:
            raise ValueError(f"Tipo '{tipo_cola}' no válido. Usa: {tipos_validos}")

        if self.tipo_cola == "FIFO":
            # Para FIFO puro, el Resource normal es más rápido y eficiente
            self.recurso = simpy.Resource(env, capacity=capacidad)
        else:
            # Para LIFO, SJF o PRIORIDAD usamos este
            self.recurso = simpy.PriorityResource(env, capacity=capacidad)

    def solicitar(self, usuario, duracion_ejercicio=0):
        """
        Genera la petición (request) con la prioridad calculada según el tipo de cola.
        """
        if self.tipo_cola == "FIFO":
            # FIFO normal no necesita prioridad
            return self.recurso.request()

        prioridad_calc = 0

        if self.tipo_cola == "PRIORIDAD":
            prioridad_calc = getattr(usuario, 'nivel_prioridad', 100)

        elif self.tipo_cola == "LIFO":
            prioridad_calc = -self.env.now

        elif self.tipo_cola == "SJF":
            # Shortest Job First: El que tarda menos entra primero.
            prioridad_calc = duracion_ejercicio

        # Devolvemos la petición con la prioridad calculada
        return self.recurso.request(priority=prioridad_calc)

    # --- Métodos de Estadística ---

    def obtener_ocupacion(self):
        return self.recurso.count

    def obtener_gente_en_espera(self):
        return len(self.recurso.queue)

    def esta_lleno(self):
        return self.recurso.count >= self.capacidad