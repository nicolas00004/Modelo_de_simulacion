import simpy
import random
import csv
import json
import os
import shutil
from datetime import datetime
from Gimnasio import Gimnasio
from usuario import Usuario


# --- 1. CLASE LOGS ---
class Logs:
    def __init__(self, nombre_base, carpeta_destino="logs"):
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)
        self.archivo_log = f"{carpeta_destino}/{nombre_base}.log"
        self.archivo_csv = f"{carpeta_destino}/{nombre_base}.csv"

        with open(self.archivo_log, "w", encoding="utf-8") as f:
            f.write(f"--- Log iniciado: {self._obtener_tiempo()} ---\n")
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
    def __init__(self, carpeta_semana, prefijo="Sim"):
        self.logger_actual = None
        self.prefijo = prefijo
        self.carpeta_semana = carpeta_semana

    def cambiar_dia(self, nombre_dia):
        nombre_archivo = f"{self.prefijo}_{nombre_dia}"
        self.logger_actual = Logs(nombre_archivo, carpeta_destino=self.carpeta_semana)

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

NOMBRES_HOMBRES = ["Juan", "Pedro", "Luis", "Carlos", "Javier", "Miguel", "Alejandro", "Pablo", "Sergio", "Daniel"]
NOMBRES_MUJERES = ["Ana", "María", "Laura", "Sofia", "Lucía", "Elena", "Carmen", "Paula", "Marta", "Isabel"]
APELLIDOS = ["García", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Ruiz", "Hernández", "Díaz", "Moreno"]


def clasificar_maquinas_por_grupo_muscular(gimnasio):
    palabras_pierna = ["Prensa", "Sentadilla", "Extensión", "Femoral", "Abductores", "Gemelos", "Hack"]
    palabras_torso = ["Press", "Jalón", "Remo", "Torre", "Dominadas", "Smith", "Scott", "Pecho"]
    for m in gimnasio.maquinas:
        if m.tipo_maquina == "Musculacion":
            es_pierna = any(p in m.nombre for p in palabras_pierna)
            es_torso = any(p in m.nombre for p in palabras_torso)
            if es_pierna:
                m.tipo_maquina = "Musculacion_Pierna"
            elif es_torso:
                m.tipo_maquina = "Musculacion_Torso"
            else:
                m.tipo_maquina = "Musculacion_Torso"


def generar_rutina_inteligente(genero):
    rutina = []
    num_ejercicios = random.randint(4, 6)
    opciones = ["Musculacion_Pierna", "Musculacion_Torso", "Cardio"]
    if genero == "Femenino":
        pesos = [0.60, 0.20, 0.20]
    else:
        pesos = [0.20, 0.60, 0.20]

    for _ in range(num_ejercicios):
        tipo_elegido = random.choices(opciones, weights=pesos, k=1)[0]
        tiempo = random.randint(15, 30) if tipo_elegido == "Cardio" else random.randint(20, 40)
        rutina.append({"tipo_maquina_deseada": tipo_elegido, "tiempo_uso": tiempo})
    return rutina


def cargar_o_crear_base_socios(archivo="datos_clientes.json", cantidad_socios=300):
    if os.path.exists(archivo):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                socios = json.load(f)
            return socios
        except:
            pass

    print(f"🆕 Generando {cantidad_socios} socios nuevos...")
    socios = []
    for i in range(1, cantidad_socios + 1):
        es_mujer = random.random() < 0.5
        genero = "Femenino" if es_mujer else "Masculino"
        nombre_pila = random.choice(NOMBRES_MUJERES) if es_mujer else random.choice(NOMBRES_HOMBRES)
        nombre = f"{nombre_pila} {random.choice(APELLIDOS)}-{i}"

        rutina_personalizada = generar_rutina_inteligente(genero)
        perfil_datos = {"tipo": "Fuerza" if random.random() < 0.7 else "Mixto", "energia": random.randint(100, 500),
                        "prob_descanso": random.uniform(0.1, 0.3)}

        socio_dict = {
            "id": i, "nombre": nombre, "genero": genero, "tipo_usuario": "Socio",
            "rutina": rutina_personalizada, "perfil": perfil_datos,
            "satisfaccion_acumulada": 100,
            "activo": True
        }
        socios.append(socio_dict)

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(socios, f, indent=4, ensure_ascii=False)
    return socios


def generar_flota_semanal_reutilizando(env, gimnasio, base_datos_socios):
    usuarios_programados = []

    # Filtro: Solo socios activos
    socios_activos = [s for s in base_datos_socios if s.get("activo", True)]
    print(f"ℹ️ Socios activos: {len(socios_activos)} / {len(base_datos_socios)}")

    if len(socios_activos) == 0:
        return []

    for dia_idx, nombre_dia in enumerate(DIAS_SEMANA):
        for sesion in range(SESIONES_POR_DIA):
            num_asistentes = int(random.uniform(0.6, 1.0) * CLIENTES_POR_SESION)
            muestra = min(num_asistentes, len(socios_activos))
            asistentes_hoy = random.sample(socios_activos, muestra)

            inicio_sesion_global = (dia_idx * MINUTOS_POR_DIA) + (sesion * DURACION_SESION)

            for datos_socio in asistentes_hoy:
                llegada = inicio_sesion_global + random.uniform(0, 15)
                fin = llegada + random.randint(60, 90)
                perfil_objeto = PerfilGenerado(datos_socio["perfil"])

                visita_usuario = Usuario(
                    id_usuario=datos_socio["id"], nombre=datos_socio["nombre"], tipo_usuario="Socio",
                    tiempo_llegada=llegada, hora_fin=fin, ocupado=False,
                    rutina=datos_socio["rutina"], perfil=perfil_objeto, problema=None,
                    env=env, gimnasio=gimnasio
                )

                satisfaccion_previa = datos_socio.get("satisfaccion_acumulada", 100)
                visita_usuario.satisfaccion = satisfaccion_previa
                usuarios_programados.append(visita_usuario)
    return usuarios_programados


def controlador_de_llegadas(env, lista_usuarios, admin_logs):
    lista_usuarios.sort(key=lambda u: u.tiempo_llegada)
    for usuario in lista_usuarios:
        tiempo_a_esperar = usuario.tiempo_llegada - env.now
        if tiempo_a_esperar > 0: yield env.timeout(tiempo_a_esperar)

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
            "tiempo_simulacion": f"{env.now:.2f}", "tipo_evento": "LLEGADA",
            "id_usuario": usuario.id, "nombre": usuario.nombre, "dia": nombre_dia,
            "sesion": sesion_del_dia + 1, "satisfaccion_inicio": usuario.satisfaccion
        })
        env.process(usuario.entrenar(tiempo_total=duracion_real))


def gestor_semanal(env, admin_logs):
    for dia in DIAS_SEMANA:
        admin_logs.cambiar_dia(dia)
        admin_logs.log(f"📅 --- INICIO DE {dia.upper()} (Min {env.now:.0f}) ---", "DIA")
        for i in range(1, SESIONES_POR_DIA + 1):
            admin_logs.log(f"🔔 Inicio Sesión {i}", "SESION")
            yield env.timeout(DURACION_SESION)
            admin_logs.log(f"🔕 Fin Sesión {i}", "SESION")
        admin_logs.log(f"🌙 --- FIN DE {dia.upper()} ---", "DIA")


def generar_conclusiones_semanales(lista_visitas, carpeta_destino, numero_semana, socios_db):
    """
    Analiza la semana, actualiza satisfacciones y registra la fecha de baja.
    """
    ruta_archivo = f"{carpeta_destino}/Conclusiones_Semana_{numero_semana}.json"
    print(f"📊 Generando reporte semanal y actualizando base de datos...")

    resultados = []
    satisfaccion_total = 0
    bajas_esta_semana = 0
    lista_bajas_detallada = []

    # Mapa temporal
    ultima_satisfaccion_map = {}

    for u in lista_visitas:
        resultados.append({
            "id": u.id, "nombre": u.nombre, "dia": u.dia_sesion,
            "sesion": u.numero_sesion, "satisfaccion_final": u.satisfaccion
        })
        satisfaccion_total += u.satisfaccion
        ultima_satisfaccion_map[u.id] = u.satisfaccion

    # --- ACTUALIZAR BASE DE DATOS Y GESTIONAR BAJAS ---
    for socio in socios_db:
        if socio["id"] in ultima_satisfaccion_map:
            nueva_satisfaccion = ultima_satisfaccion_map[socio["id"]]
            socio["satisfaccion_acumulada"] = nueva_satisfaccion

            # REGLA DE BAJA (Churn)
            if nueva_satisfaccion < 20 and socio.get("activo", True):
                # 1. Marcar como inactivo
                socio["activo"] = False

                # 2. Registrar FECHA DE BAJA en la Base de Datos
                socio["fecha_baja"] = f"Semana {numero_semana}"

                # 3. Contadores para el reporte
                bajas_esta_semana += 1
                lista_bajas_detallada.append({
                    "id": socio["id"],
                    "nombre": socio["nombre"],
                    "satisfaccion_final": nueva_satisfaccion,
                    "fecha_baja": f"Semana {numero_semana}"
                })

                print(
                    f"❌ BAJA: {socio['nombre']} (Sat: {nueva_satisfaccion}) - Fecha registrada: Semana {numero_semana}")

    # Guardar los cambios permanentes (bajas y nuevas satisfacciones) en el JSON
    with open("datos_clientes.json", "w", encoding="utf-8") as f:
        json.dump(socios_db, f, indent=4, ensure_ascii=False)

    promedio = satisfaccion_total / len(lista_visitas) if lista_visitas else 0

    informe = {
        "resumen": {
            "semana": numero_semana,
            "visitas_totales": len(lista_visitas),
            "satisfaccion_media": round(promedio, 2),
            "nuevas_bajas_cantidad": bajas_esta_semana
        },
        "detalle_bajas": lista_bajas_detallada,  # LISTA NUEVA CON NOMBRES Y FECHAS
        "detalle_visitas": resultados
    }

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(informe, f, indent=4, ensure_ascii=False)

    return bajas_esta_semana


def main():
    print("🚀 INICIANDO SIMULACIÓN MENSUAL (4 SEMANAS)...")

    carpeta_raiz = "logs_mensuales"
    if os.path.exists(carpeta_raiz):
        shutil.rmtree(carpeta_raiz)
    os.makedirs(carpeta_raiz)

    # Limpieza inicial
    if os.path.exists("datos_clientes.json"): os.remove("datos_clientes.json")
    socios_db = cargar_o_crear_base_socios("datos_clientes.json", cantidad_socios=300)

    total_bajas_acumuladas = 0

    for semana in range(1, 5):
        carpeta_semana = f"{carpeta_raiz}/Semana_{semana}"
        print(f"\n📆 --- INICIANDO SEMANA {semana} ---")

        env = simpy.Environment()
        admin_logs = AdministradorDeLogs(carpeta_semana=carpeta_semana, prefijo=f"S{semana}")

        admin_logs.cambiar_dia("SETUP")
        admin_logs.log(f"Iniciando Semana {semana}", "INIT")

        try:
            mi_gimnasio = Gimnasio()
            mi_gimnasio.cargar_datos_json("datos_gimnasio.json")
            clasificar_maquinas_por_grupo_muscular(mi_gimnasio)
            for m in mi_gimnasio.maquinas: m.iniciar_simulacion(env)
            mi_gimnasio.abrir_gimnasio()

            lista_visitas = generar_flota_semanal_reutilizando(env, mi_gimnasio, socios_db)

            if not lista_visitas:
                print("🚫 No quedan socios activos. Fin de la simulación.")
                break

            admin_logs.log(f"Visitas programadas: {len(lista_visitas)}", "SETUP")

            env.process(controlador_de_llegadas(env, lista_visitas, admin_logs))
            env.process(gestor_semanal(env, admin_logs))

            env.run(until=TIEMPO_TOTAL_SIMULACION)

            mi_gimnasio.cerrar_gimnasio()

            bajas = generar_conclusiones_semanales(lista_visitas, carpeta_semana, semana, socios_db)
            total_bajas_acumuladas += bajas

        except Exception as e:
            print(f"❌ Error en semana {semana}: {e}")
            raise e

    print(f"\n✅ MES COMPLETADO. Total bajas: {total_bajas_acumuladas}")
    print(f"📂 Revisa la carpeta 'logs_mensuales' para ver los detalles.")


if __name__ == "__main__":
    main()