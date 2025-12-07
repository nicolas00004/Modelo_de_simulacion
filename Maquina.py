import simpy
import random
from Problema import Problema


class Maquina:
    def __init__(self, nombre, id, tipo_maquina, tipo_cola, disponibilidad, durabilidad, **kwargs):
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.disponibilidad = disponibilidad
        self.durabilidad = durabilidad

        # Inicialización de variables de SimPy (se llenan en iniciar_simulacion)
        self.env = None
        self.resource = None
        self.cola = []

        # Configuración de averías (MTTF: Mean Time To Failure)
        self.tiempo_entre_averias_min = kwargs.get('mttf_min', 200)
        self.tiempo_entre_averias_max = kwargs.get('mttf_max', 400)

    def iniciar_simulacion(self, env):
        """Activa la máquina en el entorno de SimPy."""
        self.env = env
        # Capacity=1: Solo una persona a la vez
        self.resource = simpy.Resource(env, capacity=1)
        # Vinculamos la lista 'cola' al sistema interno de SimPy
        self.cola = self.resource.queue

        # Si la máquina empieza operativa, lanzamos el proceso de desgaste
        if self.disponibilidad:
            env.process(self.control_averias())

    def control_averias(self):
        """Proceso en segundo plano que rompe la máquina aleatoriamente."""
        while True:
            # 1. Tiempo de funcionamiento normal
            tiempo_hasta_rotura = random.randint(self.tiempo_entre_averias_min, self.tiempo_entre_averias_max)
            yield self.env.timeout(tiempo_hasta_rotura)

            # 2. Se produce la avería
            self.disponibilidad = False

            averia = Problema(
                tipo="AveriaMecanica",
                gravedad=random.randint(1, 3),
                descripcion=f"Fallo mecánico en {self.nombre}"
            )
            print(f"[{self.env.now:6.2f}] 💥 CRASH: {self.nombre} se ha roto (Reparación: {averia.tiempo_solucion}m).")

            # 3. El mecánico 'ocupa' la máquina para arreglarla
            # Esto impide que entren usuarios nuevos hasta que termine
            with self.resource.request() as peticion_mecanico:
                yield peticion_mecanico  # Espera a que salga el usuario actual (si lo hay)

                print(f"[{self.env.now:6.2f}] 🔧 MANTENIMIENTO: Reparando {self.nombre}...")
                yield self.env.timeout(averia.tiempo_solucion)

            # 4. Máquina reparada
            self.disponibilidad = True
            print(f"[{self.env.now:6.2f}] ✅ FIX: {self.nombre} vuelve a estar operativa.")

    def hacer(self, usuario, duracion):
        """Simula el uso de la máquina por un usuario."""
        if not self.disponibilidad:
            # Protección extra por si acaso
            print(f"[{self.env.now:6.2f}] ⚠️ {usuario.nombre} intentó usar {self.nombre} rota.")
            yield self.env.timeout(1)
            return

        yield self.env.timeout(duracion)

    def __repr__(self):
        estado = "OK" if self.disponibilidad else "ROTA"
        return f"<Maquina {self.nombre} ({estado})>"