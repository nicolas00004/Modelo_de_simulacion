import random


class Perfil:
    def __init__(self, tipo, energia=100, prob_descanso=0.1, **kwargs):
        # Recibe datos del JSON: {"tipo": "...", "energia": 100, "prob_descanso": 0.2}
        self.tipo = tipo
        self.energia = energia
        self.prob_descanso = prob_descanso

        # Configuraciones por defecto (puedes ajustarlas según el tipo de perfil)
        self.paciencia_maxima = 2  # Cuántas personas en cola soporta antes de irse

    def decidir_descanso(self):
        """Devuelve True si el usuario decide descansar en este turno."""
        return random.random() < self.prob_descanso

    def decidir_preguntar_monitor(self):
        """Devuelve True si el usuario quiere buscar un monitor (ej: 5% de prob)."""
        return random.random() < 0.05

    def tiempo_preparacion(self):
        """Tiempo en el vestuario al llegar."""
        return random.randint(5, 10)

    def tiempo_descanso(self):
        """Cuánto dura el descanso si decide tomarlo."""
        return random.randint(2, 5)

    def tiempo_busqueda_maquina(self):
        """Cuánto tiempo pierde buscando una máquina libre si todas están llenas."""
        return 1  # 1 minuto buscando

    def __repr__(self):
        return f"<Perfil {self.tipo}>"