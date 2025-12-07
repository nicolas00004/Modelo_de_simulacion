import simpy
import random
from Problema import Problema  # Importamos tu clase


class Maquina:
    def __init__(self, nombre, id, tipo_maquina, tipo_cola, disponibilidad, durabilidad, **kwargs):
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.disponibilidad = disponibilidad

        # Simulación
        self.env = None
        self.resource = None
        self.cola = []

        # CONFIGURACIÓN DE AVERÍAS (Datos por defecto o desde JSON)
        # Probabilidad de romperse: cada 200 a 400 minutos aprox
        self.tiempo_entre_averias_min = kwargs.get('mttf_min', 200)
        self.tiempo_entre_averias_max = kwargs.get('mttf_max', 400)

    def iniciar_simulacion(self, env):
        self.env = env
        self.resource = simpy.Resource(env, capacity=1)
        self.cola = self.resource.queue

        # --- NUEVO: INICIAMOS EL PROCESO DE DESGASTE/ROTURA ---
        if self.disponibilidad:  # Solo si nace viva
            env.process(self.control_averias())

    def control_averias(self):
        """Proceso fantasma que rompe la máquina periódicamente."""
        while True:
            # 1. TIEMPO DE FUNCIONAMIENTO (La máquina va bien un tiempo)
            tiempo_hasta_rotura = random.randint(self.tiempo_entre_averias_min, self.tiempo_entre_averias_max)
            yield self.env.timeout(tiempo_hasta_rotura)

            # 2. SE ROMPE (Evento)
            self.disponibilidad = False

            # Generamos un Problema para el registro/log
            averia = Problema(
                tipo="AveriaMecanica",
                gravedad=random.randint(1, 3),
                descripcion=f"Fallo en {self.nombre}"
            )
            print(f"[{self.env.now:6.2f}] 💥 CRASH: {self.nombre} se ha roto. ({averia.tiempo_solucion} min rep)")

            # OJO: Para bloquear la máquina REALMENTE en SimPy, hay un truco:
            # Creamos un usuario "fantasma" (el mecánico) que ocupa la máquina.
            # Usamos priority=-1 si usáramos PriorityResource, pero con Resource normal:

            with self.resource.request() as peticion_mecanico:
                yield peticion_mecanico  # El mecánico espera que el usuario actual termine

                # 3. TIEMPO DE REPARACIÓN (La máquina está bloqueada por el mecánico)
                print(f"[{self.env.now:6.2f}] 🔧 MECÁNICO: Reparando {self.nombre}...")
                yield self.env.timeout(averia.tiempo_solucion)

            # 4. ARREGLADA
            self.disponibilidad = True
            print(f"[{self.env.now:6.2f}] ✅ FIX: {self.nombre} vuelve a estar operativa.")

    def hacer(self, usuario, duracion):
        if not self.disponibilidad:
            # Si intentan usarla mientras está rota (por lag de simulación)
            print(f"[{self.env.now}] ⚠️ {usuario.nombre} intentó usar {self.nombre} pero estaba rota.")
            yield self.env.timeout(1)  # Pierde un minuto mirando
            return

        yield self.env.timeout(duracion)