class Accesorios:
    def __init__(self, nombre: str, cantidad: int = 1, disponibilidad: bool = True,
                 durabilidad: int = 100, **kwargs):
        """
        :param cantidad: Viene del JSON.
        :param kwargs: Absorbe cualquier otro dato extra para que no falle.
        """
        self.nombre = nombre
        self.cantidad = cantidad
        self.disponibilidad = disponibilidad
        self.durabilidad = durabilidad

        self.registro_usuario = []

    def sumar_usuario_registro(self, usuario):
        self.registro_usuario.append(usuario)

    def usar(self):
        if self.cantidad > 0:
            self.cantidad -= 1
            self.durabilidad -= 1
            # Si se acaban, ya no está disponible
            if self.cantidad == 0:
                self.disponibilidad = False

    def liberar(self):
        self.cantidad += 1
        self.disponibilidad = True

    def __repr__(self):
        return f"<Accesorio: {self.nombre} (Quedan: {self.cantidad})>"