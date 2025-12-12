import json
import random
from Accesorios import Accesorios
from Maquina import Maquina
from Monitor import Monitor


class Gimnasio:
    def __init__(self, env=None, maquinas=None, monitores=None, accesorios=None,
                 capacidad=0, n_usuarios=0, usuarios_total=0):
        # Entorno de SimPy
        self.env = env

        # Listas de componentes
        self.maquinas = maquinas if maquinas is not None else []
        self.monitores = monitores if monitores is not None else []
        self.accesorios = accesorios if accesorios is not None else []

        # Configuración base
        self.capacidad = capacidad
        self.n_usuarios = n_usuarios
        self.usuarios_total = usuarios_total

        # --- ATRIBUTOS ECONÓMICOS ---
        self.balance = 25000  # Capital inicial
        self.cuota_mensual = 50
        self.costes_reparacion_acumulados = 0

    # --- LÓGICA DE ESTADO ---

    def contar_maquinas_rotas(self):
        """Calcula cuántas máquinas tienen disponibilidad False."""
        return len([m for m in self.maquinas if hasattr(m, 'disponibilidad') and not m.disponibilidad])

    def obtener_accesorio_por_nombre(self, nombre):
        """Busca un accesorio en la lista por su nombre."""
        for acc in self.accesorios:
            if acc.nombre.lower() == nombre.lower():
                return acc
        return None

    # --- LÓGICA ECONÓMICA ---

    def cobrar_mensualidad(self, cantidad_socios_activos):
        """Inyecta ingresos al balance."""
        ingresos = cantidad_socios_activos * self.cuota_mensual
        self.balance += ingresos
        return ingresos

    def registrar_reparacion(self, coste):
        """
        Resta el coste del balance.
        Este método será llamado por Máquinas y Accesorios cuando se rompan.
        """
        self.balance -= coste
        self.costes_reparacion_acumulados += coste
        return coste

    # --- GESTIÓN DE DATOS Y CARGA ---

    def cargar_datos_json(self, archivo, env):
        """
        Carga los datos y vincula cada objeto al entorno de simulación
        y a este gimnasio (para el balance económico).
        """
        self.env = env  # Actualizamos el entorno
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            if 'configuracion' in datos:
                self.capacidad = datos['configuracion'].get('capacidad_maxima', self.capacidad)

            # Instanciamos Máquinas pasando env y referencia al gimnasio (self)
            if 'maquinas' in datos:
                self.maquinas = [Maquina(env=self.env, gimnasio=self, **m) for m in datos['maquinas']]

            # Instanciamos Monitores
            if 'monitores' in datos:
                self.monitores = [Monitor(env=self.env, **mon) for mon in datos['monitores']]

            # Instanciamos Accesorios pasando env y referencia al gimnasio
            if 'accesorios' in datos:
                self.accesorios = [Accesorios(env=self.env, gimnasio=self, **acc) for acc in datos['accesorios']]

            print(f"✅ Datos cargados y vinculados al sistema económico.")
            self.mostrar_resumen()

        except FileNotFoundError:
            print(f"❌ Error: No se encontró {archivo}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

    def mostrar_resumen(self):
        print(f"\n" + "=" * 30)
        print(f"📊 RESUMEN ACTUAL DEL GIMNASIO")
        print(f"💰 Balance: {self.balance:.2f} €")
        print(f"🔧 Maquinas Rotas: {self.contar_maquinas_rotas()}")
        print(f"🏋️ Maquinas Totales: {len(self.maquinas)}")
        print(f"📦 Accesorios: {len(self.accesorios)}")
        print("=" * 30 + "\n")

    def abrir_gimnasio(self):
        print("🚪 Gimnasio abierto para la sesión.")

    def cerrar_gimnasio(self):
        # Al cerrar, podríamos imprimir cuánto se gastó en reparaciones en esta sesión
        if self.costes_reparacion_acumulados > 0:
            print(f"🛠️ Gastos de mantenimiento en esta sesión: {self.costes_reparacion_acumulados} €")