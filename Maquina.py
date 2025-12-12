import simpy
import random
from Problema import Problema


class MachineBrokenError(Exception):
    """Excepción para indicar que la máquina se rompió durante el uso."""
    pass


class Maquina:
    def __init__(self, nombre, id, tipo_maquina, tipo_cola, disponibilidad, durabilidad=None, **kwargs):
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.disponibilidad = disponibilidad
        # Referencia al gimnasio padre se asignará post-init si no viene en kwargs
        self.gimnasio = kwargs.get("gimnasio", None)

        self.env = None
        self.resource = None
        self.cola = []
        
        # Lista para rastear a los USUARIOS (objetos) que están esperando
        # para poder interrumpirlos si la máquina se rompe.
        self.usuarios_esperando = []

        # Configuración de averías
        self.puede_romperse = True
        n = self.nombre.lower()
        if "banco" in n or "mancuerna" in n or "barra" in n or "jaula" in n:
             self.puede_romperse = False

    def iniciar_simulacion(self, env):
        """Activa la máquina en el entorno de SimPy."""
        self.env = env
        # Capacity=2: Permite compartir
        self.resource = simpy.Resource(env, capacity=2)
        self.cola = self.resource.queue

        # Si empieza rota (disponibilidad=False), lanzamos reparación
        if not self.disponibilidad:
            self.env.process(self.reparar_inmediatamente())

    def romper(self):
        """Rompe la máquina, expulsa a la cola y lanza proceso de reparación."""
        if not self.disponibilidad:
            return # Ya está rota

        self.disponibilidad = False
        print(f"[{self.env.now:6.2f}] 💥 CRASH: {self.nombre} se ha roto durante el uso!")

        # Expulsar a todos los usuarios de la cola de espera
        # Hacemos copia de la lista porque al interrumpirlos se eliminarán ellos mismos de la lista
        usuarios_a_expulsar = list(self.usuarios_esperando)
        for usuario in usuarios_a_expulsar:
            if usuario.process and usuario.process.is_alive:
                try:
                    usuario.process.interrupt(cause="MAQUINA_ROTA")
                except RuntimeError:
                    pass # Ya terminó o algo pasó
        
        # Nota: Los usuarios que la estén USANDO recibirán la excepción MachineBrokenError en su proceso 'hacer'

        # Iniciar reparación
        self.env.process(self.proceso_reparacion())

    def proceso_reparacion(self):
        # Bloquear la máquina para que nadie más entre
        # Para bloquear un Resource de SimPy, la forma más limpia es pedir todos los slots
        # con priority alta (preempt=True si fuera PreemptiveResource, pero aqui es Resource normal).
        # Como es Resource normal, tenemos que esperar a que se libre.
        # PERO, acabamos de echar a la cola. Falta echar a los que la usan.
        # Al poner self.disponibilidad = False, 'hacer' fallará.
        
        # Creamos una avería
        averia = Problema(
            tipo="AveriaMecanica",
            gravedad=random.randint(1, 3),
            descripcion=f"Fallo mecánico en {self.nombre}"
        )
        
        # Consumimos todos los slots para simular que está "ocupada por el mecánico"
        # Request con prioridad??? Resource normal no tiene prioridad.
        # Simplemente hacemos requests hasta llenar capacity.
        requests_mecanico = []
        for _ in range(self.resource.capacity):
            req = self.resource.request()
            requests_mecanico.append(req)
        
        # Esperamos a obtener todos los slots (esperamos a que salgan los usuarios actuales)
        yield simpy.AllOf(self.env, requests_mecanico)

        print(f"[{self.env.now:6.2f}] 🔧 MANTENIMIENTO: Reparando {self.nombre} ({averia.tiempo_solucion}m)...")
        
        # --- CÁLCULO DE COSTES ---
        if self.gimnasio:
            coste = random.randint(20, 300)
            self.gimnasio.registrar_reparacion(coste)
            print(f"      💸 Coste reparación: {coste}€")
            
        yield self.env.timeout(averia.tiempo_solucion)

        # Liberamos
        for req in requests_mecanico:
            self.resource.release(req)

        self.disponibilidad = True
        print(f"[{self.env.now:6.2f}] ✅ FIX: {self.nombre} vuelve a estar operativa.")

    def reparar_inmediatamente(self):
        # Helper para cuando empieza rota
        yield self.env.process(self.proceso_reparacion())

    def hacer(self, usuario, duracion):
        """Simula el uso de la máquina por un usuario."""
        if not self.disponibilidad:
            raise MachineBrokenError(f"{self.nombre} está rota.")

        # Chequeo de rotura al usar (0.01% de probabilidad - 1 en 10,000)
        # Solo si puede romperse
        if self.puede_romperse and random.random() < 0.0001:
            self.romper()
            raise MachineBrokenError(f"{self.nombre} se rompió mientras {usuario.nombre} la usaba.")

        yield self.env.timeout(duracion)

    def __repr__(self):
        estado = "OK" if self.disponibilidad else "ROTA"
        return f"<Maquina {self.nombre} ({estado})>"