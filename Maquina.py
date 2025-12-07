import json
import Tipo_Cola


class Maquina:
    # HE CAMBIADO 'disponib' por 'disponibilidad' y 'durab' por 'durabilidad'
    # para que coincidan exactamente con el JSON.
    def __init__(self, nombre: str, id: int, tipo_maquina: str, tipo_cola, disponibilidad: bool, durabilidad: int):
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.tipo_cola = tipo_cola

        # Ahora asignamos directamente
        self.disponibilidad = disponibilidad
        self.durabilidad = durabilidad

    def romper(self):
        self.disponibilidad = False
        print(f"CRASH: La máquina {self.nombre} se ha roto.")

    # Este método sigue siendo útil si quieres cargar solo máquinas,
    # pero ahora el mapeo manual ya no es necesario, podrías usar **item también.
    @classmethod
    def cargar_desde_json(cls, ruta_archivo):
        lista_maquinas = []
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            # AHORA ESTO ES MÁS SIMPLE GRACIAS AL CAMBIO DE NOMBRES
            for item in datos:
                nueva_maq = cls(**item)  # ¡Magia! Funciona porque los nombres ya coinciden
                lista_maquinas.append(nueva_maq)

            print(f"✅ Se han fabricado {len(lista_maquinas)} máquinas.")
            return lista_maquinas

        except Exception as e:
            print(f"❌ Error: {e}")
            return []