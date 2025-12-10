import json

from Accesorios import Accesorios
from Maquina import Maquina
from Monitor import Monitor



# from Usuario import Usuario  # Descomentar si tienes la clase Usuario

class Gimnasio:
    def __init__(self, maquinas=None, monitores=None, accesorios=None,
                 capacidad=0, n_usuarios=0, usuarios_total=0, usuario=None):
        self.maquinas = maquinas if maquinas is not None else []
        self.monitores = monitores if monitores is not None else []
        self.accesorios = accesorios if accesorios is not None else []
        self.usuario = usuario if usuario is not None else []

        self.capacidad = capacidad
        self.n_usuarios = n_usuarios
        self.usuarios_total = usuarios_total

    def cargar_datos_json(self, ruta_archivo):
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            if 'configuracion' in datos:
                self.capacidad = datos['configuracion'].get('capacidad_maxima', self.capacidad)
                self.n_usuarios = datos['configuracion'].get('n_usuarios_inicial', self.n_usuarios)
            if 'maquinas' in datos:
                self.maquinas = [Maquina(**m) for m in datos['maquinas']]
            if 'monitores' in datos:
                self.monitores = [Monitor(**mon) for mon in datos['monitores']]
            if 'accesorios' in datos:
                self.accesorios = [Accesorios(**acc) for acc in datos['accesorios']]

            print(f"Datos cargados correctamente desde {ruta_archivo}")
            self.mostrar_resumen()

        except FileNotFoundError:
            print(f" Error: No se encontró el archivo {ruta_archivo}")
        except json.JSONDecodeError:
            print(f" Error: El archivo {ruta_archivo} no tiene un formato JSON válido.")
        except TypeError as e:
            print(f" Error de datos: Alguna clave del JSON no coincide con el __init__ de la clase. Detalle: {e}")
        except Exception as e:
            print(f" Error inesperado: {e}")

    def mostrar_resumen(self):
        print(f"--- RESUMEN GIMNASIO ---")
        print(f"Capacidad Máxima: {self.capacidad}")
        print(f"Máquinas: {len(self.maquinas)}")
        print(f"Monitores: {len(self.monitores)}")
        print(f"Accesorios: {len(self.accesorios)}")
        print("------------------------")

    def abrir_gimnasio(self):
        print("El gimnasio está abierto.")

    def cerrar_gimnasio(self):
        print("El gimnasio está cerrado.")