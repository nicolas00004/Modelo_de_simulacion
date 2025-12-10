import random
import json
import os


class PerfilGenerado:
    def __init__(self, datos_dict):
        self.tipo = datos_dict["tipo"]
        self.energia = datos_dict["energia"]
        self.prob_descanso = datos_dict["prob_descanso"]
        self.paciencia_maxima = random.randint(2, 5)

    def tiempo_preparacion(self): return random.randint(3, 8)

    def decidir_descanso(self): return random.random() < self.prob_descanso

    def tiempo_descanso(self): return random.randint(1, 3)

    def decidir_preguntar_monitor(self): return random.random() < 0.15

    def tiempo_pregunta_monitor(self): return random.randint(2, 5)

    def decidir_usar_accesorio(self): return random.random() < 0.20

    def tiempo_uso_accesorio(self): return random.randint(5, 15)


class GestorSocios:
    def __init__(self, config):
        self.config = config
        self.ruta_db = config.datos["rutas"]["archivo_clientes"]
        self.nombres_h = ["Juan", "Pedro", "Luis", "Carlos", "Javier", "Miguel", "Alejandro", "Pablo"]
        self.nombres_m = ["Ana", "María", "Laura", "Sofia", "Lucía", "Elena", "Carmen", "Paula"]
        self.apellidos = ["García", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Ruiz"]

    def generar_rutina(self, genero):
        rutina = []
        opciones = ["Musculacion_Pierna", "Musculacion_Torso", "Cardio"]
        pesos = [0.60, 0.20, 0.20] if genero == "Femenino" else [0.20, 0.60, 0.20]
        for _ in range(random.randint(4, 6)):
            tipo = random.choices(opciones, weights=pesos, k=1)[0]
            tiempo = random.randint(15, 30) if tipo == "Cardio" else random.randint(20, 40)
            rutina.append({"tipo_maquina_deseada": tipo, "tiempo_uso": tiempo})
        return rutina

    def generar_lote(self, cantidad, id_inicial, mes_origen):
        lote = []
        prob_baja = self.config.datos["simulacion"]["probabilidad_baja_historica"]
        for i in range(cantidad):
            nuevo_id = id_inicial + i
            es_mujer = random.random() < 0.5
            genero = "Femenino" if es_mujer else "Masculino"
            nombre = f"{random.choice(self.nombres_m if es_mujer else self.nombres_h)} {random.choice(self.apellidos)}-{nuevo_id}"

            es_baja = (mes_origen == "Carga_Inicial" and random.random() < prob_baja)
            activo = not es_baja
            satisfaccion = random.randint(0, 19) if es_baja else 100

            socio = {
                "id": nuevo_id, "nombre": nombre, "genero": genero, "tipo_usuario": "Socio",
                "mes_alta": mes_origen, "rutina": self.generar_rutina(genero),
                "perfil": {"tipo": "Fuerza", "energia": 300, "prob_descanso": 0.2},
                "satisfaccion_acumulada": satisfaccion, "activo": activo, "faltas_consecutivas": 0,
                "castigado_hasta_semana_absoluta": 0, "fecha_baja": "Pre-Simulacion" if es_baja else None
            }
            lote.append(socio)
        return lote

    def inicializar_db(self):
        if os.path.exists(self.ruta_db): os.remove(self.ruta_db)
        cantidad = self.config.datos["simulacion"].get("usuarios_totales_iniciales", 300)
        print(f"🆕 Generando BASE INICIAL: {cantidad} socios...")
        socios = self.generar_lote(cantidad, 1, "Carga_Inicial")
        with open(self.ruta_db, "w", encoding="utf-8") as f: json.dump(socios, f, indent=4)
        return socios

    def inyectar_nuevos(self, socios_actuales, cantidad, mes):
        if cantidad <= 0: return socios_actuales
        real = int(random.uniform(0.8, 1.2) * cantidad)
        last_id = socios_actuales[-1]["id"]
        print(f"✨ ALTAS {mes}: +{real} socios.")
        nuevos = self.generar_lote(real, last_id + 1, mes)
        socios_actuales.extend(nuevos)
        with open(self.ruta_db, "w", encoding="utf-8") as f: json.dump(socios_actuales, f, indent=4)
        return socios_actuales