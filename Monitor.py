import random

class Monitor:
    def __init__(self, nombre, id, especialidad, env=None, **kwargs):
        # NOTA: Los argumentos coinciden con el JSON:
        # {"nombre": "Carlos", "id": "M01", "especialidad": "Musculacion"}
        self.nombre = nombre
        self.id = id
        self.especialidad = especialidad
        self.env = env

        self.cola = []

    def preguntar(self, usuario):
        # Añadir a la cola
        self.cola.append(usuario)
        try:
            print(f"[{usuario.env.now:.2f}] 🗣️ {usuario.nombre} espera al monitor {self.nombre}...")

            # MODIFICACIÓN: Cálculo del tiempo con distribución triangular
            # random.triangular(minimo, maximo, moda)
            # - low (2): Nadie tarda menos de 2 minutos.
            # - high (10): Nadie tarda más de 10 minutos.
            # - mode (5): Lo más habitual es tardar 5 minutos.
            tiempo_atencion = random.triangular(2, 10, 5)

            # Simulamos el tiempo que tarda en atender usando el valor calculado
            yield usuario.env.timeout(tiempo_atencion)

            print(f"[{usuario.env.now:.2f}] ✅ {self.nombre} aconsejó a {usuario.nombre} (duración: {tiempo_atencion:.2f}m).")
        finally:
            # Aseguramos que se quite de la cola pase lo que pase
            self.cola.remove(usuario)

    def __repr__(self):
        return f"<Monitor: {self.nombre}>"