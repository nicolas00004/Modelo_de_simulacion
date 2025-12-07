class Monitor:
    def __init__(self, nombre, id, especialidad):
        # NOTA: Los argumentos coinciden con el JSON:
        # {"nombre": "Carlos", "id": "M01", "especialidad": "Musculacion"}
        self.nombre = nombre
        self.id = id
        self.especialidad = especialidad

        # Inicializamos la cola vacía internamente (no viene del JSON)
        self.cola = []

    def preguntar(self, usuario):
        """
        Método llamado por el Usuario.
        """
        # Añadir a la cola
        self.cola.append(usuario)
        try:
            print(f"[{usuario.env.now:.2f}] 🗣️ {usuario.nombre} espera al monitor {self.nombre}...")

            # Simulamos el tiempo que tarda en atender (ej: 5 minutos)
            # Usamos usuario.env porque el Monitor no guarda el entorno
            yield usuario.env.timeout(5)

            print(f"[{usuario.env.now:.2f}] ✅ {self.nombre} aconsejó a {usuario.nombre}.")
        finally:
            # Aseguramos que se quite de la cola pase lo que pase
            self.cola.remove(usuario)

    def __repr__(self):
        return f"<Monitor: {self.nombre}>"