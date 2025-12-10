import simpy
import random
import csv
import json
import os
from datetime import datetime
from Gimnasio import Gimnasio
from usuario import Usuario


# --- 1. CLASE LOGS ---
class Logs:
    def __init__(self, nombre_base):
        if not os.path.exists("logs"):
            os.makedirs("logs")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archivo_log = f"logs/{nombre_base}_{timestamp}.log"
        self.archivo_csv = f"logs/{nombre_base}_{timestamp}.csv"
        with open(self.archivo_log, "w", encoding="utf-8") as f:
            f.write(f"--- Experimento iniciado el {self._obtener_tiempo()} ---\n")
        self.cabeceras_escritas = False

    def _obtener_tiempo(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, mensaje, nivel="INFO"):
        linea = f"[{self._obtener_tiempo()}] [{nivel}] {mensaje}\n"
        with open(self.archivo_log, "a", encoding="utf-8") as f:
            f.write(linea)

    def log_parametros(self, **kwargs):
        self.log("--- CONFIGURACIÓN ---", "SETUP")
        for k, v in kwargs.items():
            self.log(f"{k}: {v}", "PARAM")
        self.log("---------------------", "SETUP")

    def registrar_datos(self, datos: dict):
        try:
            with open(self.archivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=datos.keys())
                if not self.cabeceras_escritas:
                    writer.writeheader()
                    self.cabeceras_escritas = True
                writer.writerow(datos)
        except Exception as e:
            self.log(f"Error CSV: {e}", "ERROR")


# --- 2. ADMINISTRADOR DE LOGS ---
class AdministradorDeLogs:
    def __init__(self, prefijo="Simulacion"):
        self.logger_actual = None
        self.prefijo = prefijo

    def cambiar_dia(self, nombre_dia):
        if self.logger_actual:
            print(f"--- Cerrando log del día anterior ---")
        nombre_archivo = f"{self.prefijo}_{nombre_dia}"
        self.logger_actual = Logs(nombre_archivo)
        print(f"📁 Nuevo log activo: {nombre_archivo}")

    def log(self, mensaje, nivel="INFO"):
        if self.logger_actual: self.logger_actual.log(mensaje, nivel)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)

    def log_parametros(self, **kwargs):
        if self.logger_actual: self.logger_actual.log_parametros(**kwargs)


# --- 3. PERFIL GENERADO ---
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


# --- CONFIGURACIÓN ---
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
SESIONES_POR_DIA = 6
DURACION_SESION = 90
CLIENTES_POR_SESION = 50
MINUTOS_POR_DIA = SESIONES_POR_DIA * DURACION_SESION
TIEMPO_TOTAL_SIMULACION = MINUTOS_POR_DIA * len(DIAS_SEMANA)

# --- GENERACIÓN DE DATOS BASE ---
NOMBRES = ["Ana", "Beto", "Carla", "Dani", "Elena", "Fede", "Gabi", "Hugo",
           "Inés", "Juan", "Katia", "Luis", "Marta", "Nacho", "Olga", "Pablo",
           "Quique", "Rosa", "Sara", "Tito", "Ursula", "Victor", "Wendy", "Xavi"]

APELLIDOS = ["García", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Ruiz",
             "Hernández", "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero", "Alonso",
             "Gutiérrez", "Navarro", "Torres", "Domínguez", "Vázquez", "Ramos", "Gil"]

RUTINAS_TEMPLATE = [
    {"rutina": [{"tipo_maquina_deseada": "Cardio", "tiempo_uso": 40},
                {"tipo_maquina_deseada": "Cardio", "tiempo_uso": 30}],
     "perfil": {"tipo": "Resistencia", "energia": 300, "prob_descanso": 0.05}},
    {"rutina": [{"tipo_maquina_deseada": "Musculacion", "tiempo_uso": 30},
                {"tipo_maquina_deseada": "Musculacion", "tiempo_uso": 30},
                {"tipo_maquina_deseada": "Musculacion", "tiempo_uso": 20}],
     "perfil": {"tipo": "Fuerza", "energia": 400, "prob_descanso": 0.2}},
    {"rutina": [{"tipo_maquina_deseada": "Cardio", "tiempo_uso": 20},
                {"tipo_maquina_deseada": "Musculacion", "tiempo_uso": 30},
                {"tipo_maquina_deseada": "Cardio", "tiempo_uso": 20}],
     "perfil": {"tipo": "Híbrido", "energia": 200, "prob_descanso": 0.1}},
    {"rutina": [{"tipo_maquina_deseada": "Cardio", "tiempo_uso": 15},
                {"tipo_maquina_deseada": "Musculacion", "tiempo_uso": 20}],
     "perfil": {"tipo": "Prisas", "energia": 100, "prob_descanso": 0.0}}
]


def cargar_o_crear_base_socios(archivo="datos_clientes.json", cantidad_socios=200):
    if os.path.exists(archivo):
        print(f"📂 Cargando base de datos de socios desde {archivo}...")
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                socios = json.load(f)
            print(f"✅ Se han cargado {len(socios)} socios registrados.")
            return socios
        except Exception as e:
            print(f"⚠️ Error leyendo JSON ({e}). Generando nuevos socios...")

    print(f"🆕 Generando {cantidad_socios} socios nuevos para la base de datos...")
    socios = []
    for i in range(1, cantidad_socios + 1):
        template = random.choice(RUTINAS_TEMPLATE)
        nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}-{i}"

        socio_dict = {
            "id": i,
            "nombre": nombre,
            "tipo_usuario": "Socio",
            "rutina": template["rutina"],
            "perfil": template["perfil"]
        }
        socios.append(socio_dict)

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(socios, f, indent=4, ensure_ascii=False)

    return socios


def generar_flota_semanal_reutilizando(env, gimnasio, base_datos_socios):
    usuarios_programados = []
    for dia_idx, nombre_dia in enumerate(DIAS_SEMANA):
        for sesion in range(SESIONES_POR_DIA):
            num_asistentes = int(random.uniform(0.4, 1.0) * CLIENTES_POR_SESION)
            asistentes_hoy = random.sample(base_datos_socios, min(num_asistentes, len(base_datos_socios)))

            inicio_sesion_global = (dia_idx * MINUTOS_POR_DIA) + (sesion * DURACION_SESION)

            for datos_socio in asistentes_hoy:
                llegada = inicio_sesion_global + random.uniform(0, 15)
                fin = llegada + random.randint(50, 80)

                perfil_objeto = PerfilGenerado(datos_socio["perfil"])

                visita_usuario = Usuario(
                    id_usuario=datos_socio["id"],
                    nombre=datos_socio["nombre"],
                    tipo_usuario="Socio Recurrente",
                    tiempo_llegada=llegada,
                    hora_fin=fin,
                    ocupado=False,
                    rutina=datos_socio["rutina"],
                    perfil=perfil_objeto,
                    problema=None,
                    env=env,
                    gimnasio=gimnasio
                )
                usuarios_programados.append(visita_usuario)
    return usuarios_programados


# --- FUNCIÓN NUEVA: EXPORTAR CONCLUSIONES FINALES ---
def generar_conclusiones(lista_usuarios_simulados, nombre_archivo="conclusiones.json"):
    """
    Recorre todas las visitas simuladas y genera un resumen con la satisfacción final.
    """
    print(f"\n📊 Generando informe de conclusiones en '{nombre_archivo}'...")

    resultados = []
    satisfaccion_total = 0
    usuarios_con_problemas = 0

    for usuario in lista_usuarios_simulados:

        # Detectamos si tuvo una mala experiencia
        mala_experiencia = usuario.satisfaccion < 60
        if mala_experiencia:
            usuarios_con_problemas += 1

        resultados.append({
            "id": usuario.id,
            "nombre": usuario.nombre,
            "dia": usuario.dia_sesion,
            "sesion": usuario.numero_sesion,
            "satisfaccion_final": usuario.satisfaccion,
            "experiencia": "Mala" if mala_experiencia else "Buena",
            "perfil": usuario.perfil.tipo
        })

        satisfaccion_total += usuario.satisfaccion

    # Calculamos promedios globales
    total_visitas = len(lista_usuarios_simulados)
    promedio_satisfaccion = satisfaccion_total / total_visitas if total_visitas > 0 else 0

    informe_final = {
        "resumen_semanal": {
            "total_visitas": total_visitas,
            "satisfaccion_media_global": round(promedio_satisfaccion, 2),
            "visitas_con_mala_experiencia": usuarios_con_problemas,
            "porcentaje_quejas": f"{(usuarios_con_problemas / total_visitas) * 100:.1f}%"
        },
        "detalle_visitas": resultados
    }

    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(informe_final, f, indent=4, ensure_ascii=False)
        print("✅ Informe generado correctamente.")
    except Exception as e:
        print(f"❌ Error generando informe: {e}")


def controlador_de_llegadas(env, lista_usuarios, admin_logs):
    lista_usuarios.sort(key=lambda u: u.tiempo_llegada)
    for usuario in lista_usuarios:
        tiempo_a_esperar = usuario.tiempo_llegada - env.now
        if tiempo_a_esperar > 0:
            yield env.timeout(tiempo_a_esperar)

        dia_actual_idx = int(env.now // MINUTOS_POR_DIA)
        if dia_actual_idx >= len(DIAS_SEMANA): break

        nombre_dia = DIAS_SEMANA[dia_actual_idx]
        minuto_del_dia = env.now % MINUTOS_POR_DIA
        sesion_del_dia = int(minuto_del_dia // DURACION_SESION)
        fin_sesion_global = (dia_actual_idx * MINUTOS_POR_DIA) + ((sesion_del_dia + 1) * DURACION_SESION)
        tiempo_restante = fin_sesion_global - env.now

        duracion_deseada = usuario.hora_fin - usuario.tiempo_llegada
        if duracion_deseada <= 0: duracion_deseada = 60
        duracion_real = min(duracion_deseada, tiempo_restante)

        if duracion_real < 5: continue

        usuario.logger_sesion = admin_logs
        usuario.dia_sesion = nombre_dia
        usuario.numero_sesion = sesion_del_dia + 1

        mensaje = f"➕ {usuario.nombre} entra ({nombre_dia} - Sesión {sesion_del_dia + 1})"
        admin_logs.log(mensaje, "LLEGADA")

        admin_logs.registrar_datos({
            "tiempo_simulacion": f"{env.now:.2f}",
            "tipo_evento": "LLEGADA",
            "id_usuario": usuario.id,
            "nombre": usuario.nombre,
            "dia": nombre_dia,
            "sesion": sesion_del_dia + 1,
            "duracion_real": duracion_real
        })

        env.process(usuario.entrenar(tiempo_total=duracion_real))


def gestor_semanal(env, admin_logs):
    for dia in DIAS_SEMANA:
        admin_logs.cambiar_dia(dia)
        admin_logs.log(f"📅 --- INICIO DE {dia.upper()} (Min {env.now:.0f}) ---", "DIA")
        print(f"\n >>> 📅 INICIO {dia.upper()} <<<")

        for i in range(1, SESIONES_POR_DIA + 1):
            admin_logs.log(f"🔔 Inicio Sesión {i} de {dia}", "SESION")
            print(f"   [Min {env.now:.0f}] 🔔 Sesión {i}")
            yield env.timeout(DURACION_SESION)
            admin_logs.log(f"🔕 Fin Sesión {i} de {dia}", "SESION")

        admin_logs.log(f"🌙 --- FIN DE {dia.upper()} ---", "DIA")


def main():
    admin_logs = AdministradorDeLogs(prefijo="GymSim")
    admin_logs.cambiar_dia("SETUP")

    admin_logs.log("========================================", "INIT")
    admin_logs.log(f"   SIMULACIÓN SEMANAL (L-V)            ", "INIT")
    admin_logs.log(f"   REUTILIZANDO CLIENTES DEL JSON      ", "INIT")
    admin_logs.log("========================================", "INIT")

    env = simpy.Environment()

    try:
        mi_gimnasio = Gimnasio()
        mi_gimnasio.cargar_datos_json("datos_gimnasio.json")
        for maquina in mi_gimnasio.maquinas:
            maquina.iniciar_simulacion(env)
        mi_gimnasio.abrir_gimnasio()
        admin_logs.log("Infraestructura cargada.", "SETUP")

        socios_db = cargar_o_crear_base_socios("datos_clientes.json", cantidad_socios=200)
        admin_logs.log(f"Base de datos de socios cargada: {len(socios_db)} registros.", "SETUP")

        admin_logs.log("Programando visitas semanales...", "SETUP")
        lista_visitas = generar_flota_semanal_reutilizando(env, mi_gimnasio, socios_db)
        admin_logs.log(f"¡Programadas {len(lista_visitas)} visitas en total!", "SETUP")

        env.process(controlador_de_llegadas(env, lista_visitas, admin_logs))
        env.process(gestor_semanal(env, admin_logs))

        admin_logs.log("--- INICIANDO RUN ---", "RUN")

        env.run(until=TIEMPO_TOTAL_SIMULACION)

        print("\n========================================")
        print("✅ Simulación completada.")

        # --- AQUÍ GENERAMOS EL REPORTE FINAL ---
        generar_conclusiones(lista_visitas, "conclusiones.json")

        mi_gimnasio.cerrar_gimnasio()

    except Exception as e:
        admin_logs.log(f"Error crítico: {e}", "FATAL")
        raise e


if __name__ == "__main__":
    main()