import json
import os
import random


class PerfilGenerado:
    def __init__(self, datos_dict):
        self.tipo = datos_dict.get("tipo", "Mix")
        self.energia = datos_dict.get("energia", 200)
        self.prob_descanso = datos_dict.get("prob_descanso", 0.2)
        # Paciencia variable: determina cuánto está dispuesto a esperar en colas
        self.paciencia_maxima = random.randint(3, 7)

    def tiempo_preparacion(self): return random.randint(3, 8)

    def decidir_descanso(self): return random.random() < self.prob_descanso

    def tiempo_descanso(self): return random.randint(1, 4)

    def decidir_preguntar_monitor(self): return random.random() < 0.10

    # Lógica para interactuar con accesorios (pesas, esterillas, etc.)
    def decidir_usar_accesorio(self):
        prob = 0.40 if self.tipo == "Fuerza" else 0.15
        return random.random() < prob

    def tiempo_uso_accesorio(self): return random.randint(5, 12)


class GestorSocios:
    def __init__(self, config):
        self.config = config
        self.ruta_db = config.datos["rutas"]["archivo_clientes"]

        # Listas para generar identidades realistas
        self.nombres_h = ["Juan", "Pedro", "Luis", "Carlos", "Javier", "Miguel", "Alejandro", "Pablo", "Sergio",
                          "Daniel"]
        self.nombres_m = ["Ana", "María", "Laura", "Sofia", "Lucía", "Elena", "Carmen", "Paula", "Marta", "Isabel"]
        self.apellidos = ["García", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Ruiz", "Hernández", "Díaz",
                          "Moreno"]

        self.mapa_meses = {
            "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7
        }

    def generar_lote(self, cantidad, id_inicial, mes_origen):
        """Crea un grupo de nuevos socios con nombres y perfiles aleatorios."""
        lote = []
        for i in range(cantidad):
            nuevo_id = id_inicial + i
            es_mujer = random.random() < 0.5
            genero = "Femenino" if es_mujer else "Masculino"

            # Generación de nombre real
            nombre_pila = random.choice(self.nombres_m if es_mujer else self.nombres_h)
            apellido = random.choice(self.apellidos)
            nombre_completo = f"{nombre_pila} {apellido}"

            # Clasificación del socio
            roll = random.random()
            if roll < 0.65:
                subtipo = "Estudiante"
            elif roll < 0.90:
                subtipo = "Trabajador"
            else:
                subtipo = "Egresado"

            plan = "Mensual" if subtipo == "Egresado" or random.random() < 0.6 else "Anual"

            socio = {
                "id": nuevo_id,
                "nombre": nombre_completo,
                "genero": genero,
                "subtipo": subtipo,
                "plan_pago": plan,
                "mes_alta": mes_origen,
                "fecha_alta": f"{random.randint(1, 28)}-{self.mapa_meses.get(mes_origen, 9)}-2023",
                "rutina": self._generar_rutina_por_genero(genero),
                "perfil": self._generar_perfil_aleatorio(),
                "satisfaccion_acumulada": 100,
                "activo": True,
                "faltas_consecutivas": 0,
                "fecha_baja": None
            }
            lote.append(socio)
        return lote

    def _generar_rutina_por_genero(self, genero):
        opciones = ["Musculacion_Pierna", "Musculacion_Torso", "Cardio"]
        pesos = [0.6, 0.2, 0.2] if genero == "Femenino" else [0.2, 0.6, 0.2]
        return [{"tipo_maquina_deseada": random.choices(opciones, weights=pesos)[0],
                 "tiempo_uso": random.randint(15, 35)} for _ in range(random.randint(4, 6))]

    def _generar_perfil_aleatorio(self):
        tipos = ["Fuerza", "Cardio", "Mix"]
        return {"tipo": random.choice(tipos), "energia": random.randint(150, 350),
                "prob_descanso": random.uniform(0.1, 0.4)}

    def inyectar_nuevos(self, socios_actuales, cantidad_aprox, mes):
        """Añade nuevos socios a la base de datos (Picos de Septiembre/Enero)."""
        if cantidad_aprox <= 0: return socios_actuales
        cantidad_real = int(random.uniform(0.9, 1.1) * cantidad_aprox)
        last_id = socios_actuales[-1]["id"] if socios_actuales else 100
        nuevos = self.generar_lote(cantidad_real, last_id + 1, mes)
        socios_actuales.extend(nuevos)
        self._guardar_db(socios_actuales)
        return socios_actuales

    def inicializar_db(self):
        """Genera la población inicial del gimnasio."""
        iniciales = self.config.datos["simulacion"].get("usuarios_totales_iniciales", 300)
        socios = self.generar_lote(iniciales, 100, "Septiembre")
        self._guardar_db(socios)
        return socios

    def _guardar_db(self, lista_socios):
        with open(self.ruta_db, "w", encoding="utf-8") as f:
            json.dump(lista_socios, f, indent=4, ensure_ascii=False)