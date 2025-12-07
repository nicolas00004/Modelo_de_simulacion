class Problema:
    def __init__(self, tipo: str, gravedad: int = 1, tiempo_solucion: int = 10, descripcion: str = "", id: int = 0,
                 **kwargs):
        """
        :param tipo: Tipo de problema (ej: "LesionRodilla") -> OBLIGATORIO en JSON
        :param gravedad: (Opcional) Nivel de gravedad
        :param tiempo_solucion: (Opcional) Tiempo que tarda el monitor en arreglarlo
        :param descripcion: (Opcional) Texto extra
        :param id: (Opcional) Identificador
        :param kwargs: Captura cualquier otro dato extra del JSON para que no de error
        """
        self.tipo = tipo
        self.gravedad = gravedad

        # Corregí el error tipográfico: tiempo_solcuion -> tiempo_solucion
        # Si el JSON no trae tiempo, calculamos uno basado en la gravedad (lógica opcional)
        if tiempo_solucion is None:
            self.tiempo_solucion = gravedad * 5
        else:
            self.tiempo_solucion = tiempo_solucion

        self.descripcion = descripcion
        self.id = id

    def __repr__(self):
        return f"<Problema: {self.tipo} (Tiempo: {self.tiempo_solucion}m)>"