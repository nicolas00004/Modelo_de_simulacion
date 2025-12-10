import simpy
import random
import csv
import json
import os
import shutil
from datetime import datetime
from collections import Counter
from Gimnasio import Gimnasio
from usuario import Usuario


# --- CARGAR CONFIGURACIÓN GLOBAL ---
def cargar_configuracion():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: No se encuentra 'config.json'. Usando valores por defecto.")
        return {
            "simulacion": {
                "duracion_sesion_minutos": 90,
                "clientes_base_por_sesion": 50,
                "usuarios_totales_iniciales": 300,  # Valor por defecto si falla el json
                "probabilidad_baja_historica": 0.15,
                "variacion_afluencia": 0.2
            },
            "satisfaccion": {"umbral_baja_novato": 40, "umbral_baja_medio": 25, "umbral_baja_veterano": 10,
                             "penalizacion_espera_cola": 0.5, "penalizacion_maquina_rota": 10,
                             "penalizacion_sin_maquina": 3, "minutos_paciencia_cola": 4},
            "rutas": {"archivo_clientes": "datos_clientes.json", "archivo_gym": "datos_gimnasio.json",
                      "carpeta_logs": "logs_anuales"}
        }


CONFIG = cargar_configuracion()


# --- 1. CLASE LOGS ---
class Logs:
    def __init__(self, ruta_completa_sin_ext):
        carpeta = os.path.dirname(ruta_completa_sin_ext)
        if not os.path.exists(carpeta): os.makedirs(carpeta)

        self.archivo_txt = f"{ruta_completa_sin_ext}.txt"
        self.archivo_csv = f"{ruta_completa_sin_ext}.csv"

        with open(self.archivo_txt, "w", encoding="utf-8") as f:
            f.write(f"--- Sesión iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

        self.cabeceras_escritas = False
        self.fieldnames = ["tiempo_simulacion", "tipo_evento", "id_usuario", "nombre", "dia", "sesion",
                           "satisfaccion_actual", "satisfaccion_inicio", "maquina", "duracion", "cola_tamano",
                           "extra_info"]

        with open(self.archivo_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def _obtener_tiempo(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, mensaje, nivel="INFO"):
        with open(self.archivo_txt, "a", encoding="utf-8") as f:
            f.write(f"[{self._obtener_tiempo()}] [{nivel}] {mensaje}\n")

    def registrar_datos(self, datos):
        try:
            datos_filtrados = {k: v for k, v in datos.items() if k in self.fieldnames}
            with open(self.archivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(datos_filtrados)
        except Exception:
            pass

    def log_parametros(self, **kwargs):
        self.log("--- SETUP ---")
        for k, v in kwargs.items(): self.log(f"{k}: {v}")


# --- 2. ADMINISTRADOR DE LOGS ---
class AdministradorDeLogs:
    def __init__(self, carpeta_semana):
        self.logger_actual = None
        self.carpeta_semana = carpeta_semana

    def cambiar_sesion(self, nombre_dia, numero_sesion):
        # MODO LIMPIO: Descomenta la linea de abajo si quieres logs por sesión
        # self.logger_actual = Logs(f"{self.carpeta_semana}/{nombre_dia}/Sesion_{numero_sesion}")
        self.logger_actual = None

    def log(self, mensaje, nivel="INFO"):
        if self.logger_actual: self.logger_actual.log(mensaje, nivel)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)


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


# --- CALENDARIO Y CONSTANTES ---
CALENDARIO_ACADEMICO = [
    {"mes": "Septiembre", "semanas": 4, "peso_afluencia": 1.2, "nuevas_altas_aprox": 50, "abierto": True},
    {"mes": "Octubre", "semanas": 4, "peso_afluencia": 1.0, "nuevas_altas_aprox": 20, "abierto": True},
    {"mes": "Noviembre", "semanas": 4, "peso_afluencia": 0.9, "nuevas_altas_aprox": 15, "abierto": True},
    {"mes": "Diciembre", "semanas": 3, "peso_afluencia": 0.5, "nuevas_altas_aprox": 5, "abierto": True},
    {"mes": "Navidad", "semanas": 0, "peso_afluencia": 0.0, "nuevas_altas_aprox": 0, "abierto": False},
    {"mes": "Enero", "semanas": 4, "peso_afluencia": 1.5, "nuevas_altas_aprox": 100, "abierto": True},
    {"mes": "Febrero", "semanas": 4, "peso_afluencia": 1.3, "nuevas_altas_aprox": 40, "abierto": True},
    {"mes": "Marzo", "semanas": 4, "peso_afluencia": 1.1, "nuevas_altas_aprox": 20, "abierto": True},
    {"mes": "Abril", "semanas": 4, "peso_afluencia": 0.9, "nuevas_altas_aprox": 10, "abierto": True},
    {"mes": "Mayo", "semanas": 4, "peso_afluencia": 1.3, "nuevas_altas_aprox": 30, "abierto": True},
    {"mes": "Junio", "semanas": 3, "peso_afluencia": 0.8, "nuevas_altas_aprox": 5, "abierto": True}
]

INDICE_MESES = {m["mes"]: i for i, m in enumerate(CALENDARIO_ACADEMICO) if m["mes"] != "Navidad"}
INDICE_MESES["Carga_Inicial"] = -1

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

NOMBRES_HOMBRES = ["Juan", "Pedro", "Luis", "Carlos", "Javier", "Miguel", "Alejandro", "Pablo", "Sergio", "Daniel"]
NOMBRES_MUJERES = ["Ana", "María", "Laura", "Sofia", "Lucía", "Elena", "Carmen", "Paula", "Marta", "Isabel"]
APELLIDOS = ["García", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Ruiz", "Hernández", "Díaz", "Moreno"]

DURACION_SESION = CONFIG["simulacion"]["duracion_sesion_minutos"]
CLIENTES_BASE = CONFIG["simulacion"]["clientes_base_por_sesion"]
SESIONES_DIA_LABORAL = 9
SESIONES_SABADO = 4
MINUTOS_MAXIMOS_POR_DIA = 9 * DURACION_SESION
TIEMPO_SEMANAL_SIMULACION = MINUTOS_MAXIMOS_POR_DIA * len(DIAS_SEMANA)


def obtener_sesiones_por_dia(dia):
    return SESIONES_SABADO if dia == "Sábado" else SESIONES_DIA_LABORAL


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


def generar_lote_socios(cantidad, id_inicial, mes_origen):
    lote = []
    prob_baja = CONFIG["simulacion"]["probabilidad_baja_historica"]

    for i in range(cantidad):
        nuevo_id = id_inicial + i
        es_mujer = random.random() < 0.5
        genero = "Femenino" if es_mujer else "Masculino"
        nombre_pila = random.choice(NOMBRES_MUJERES) if es_mujer else random.choice(NOMBRES_HOMBRES)
        nombre = f"{nombre_pila} {random.choice(APELLIDOS)}-{nuevo_id}"
        rutina = generar_rutina_inteligente(genero)
        perfil = {"tipo": "Fuerza" if random.random() < 0.7 else "Mixto", "energia": random.randint(100, 500),
                  "prob_descanso": random.uniform(0.1, 0.3)}

        es_baja_historica = False
        if mes_origen == "Carga_Inicial":
            es_baja_historica = random.random() < prob_baja

        if es_baja_historica:
            activo = False;
            satisfaccion = random.randint(0, 19);
            fecha_baja = "Pre-Simulacion"
        else:
            activo = True;
            satisfaccion = 100;
            fecha_baja = None

        socio = {
            "id": nuevo_id, "nombre": nombre, "genero": genero, "tipo_usuario": "Socio",
            "mes_alta": mes_origen, "rutina": rutina, "perfil": perfil,
            "satisfaccion_acumulada": satisfaccion, "activo": activo,
            "faltas_consecutivas": 0, "castigado_hasta_semana_absoluta": 0,
            "fecha_baja": fecha_baja
        }
        lote.append(socio)
    return lote


def inicializar_base_datos(archivo, cantidad_inicial):
    if os.path.exists(archivo): os.remove(archivo)
    print(f"🆕 Generando BASE INICIAL (Pre-Septiembre): {cantidad_inicial} socios...")
    socios = generar_lote_socios(cantidad_inicial, id_inicial=1, mes_origen="Carga_Inicial")
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(socios, f, indent=4, ensure_ascii=False)
    return socios


def inyectar_socios_nuevos(socios_actuales, cantidad_objetivo, mes_actual):
    if cantidad_objetivo <= 0: return socios_actuales
    cantidad_real = int(random.uniform(0.8, 1.2) * cantidad_objetivo)
    ultimo_id = socios_actuales[-1]["id"]
    print(f"✨ ALTAS {mes_actual.upper()}: Registrando {cantidad_real} usuarios nuevos...")
    nuevos_socios = generar_lote_socios(cantidad_real, id_inicial=ultimo_id + 1, mes_origen=mes_actual)
    socios_actuales.extend(nuevos_socios)
    with open(CONFIG["rutas"]["archivo_clientes"], "w", encoding="utf-8") as f:
        json.dump(socios_actuales, f, indent=4, ensure_ascii=False)
    return socios_actuales


def generar_flota_semanal_reutilizando(env, gimnasio, base_datos_socios, semana_absoluta, factor_afluencia):
    usuarios_programados = []

    socios_activos = [s for s in base_datos_socios if
                      s.get("activo", True) and s.get("castigado_hasta_semana_absoluta", 0) < semana_absoluta]

    cupo_sesion = int(CLIENTES_BASE * factor_afluencia)
    print(f"   ℹ️ Socios activos DB: {len(socios_activos)} | Cupo: ~{cupo_sesion} pax/sesión")

    if not socios_activos: return []

    for dia_idx, nombre_dia in enumerate(DIAS_SEMANA):
        num_sesiones = obtener_sesiones_por_dia(nombre_dia)
        socios_reservados_hoy = set()

        for sesion in range(num_sesiones):
            variacion = CONFIG["simulacion"]["variacion_afluencia"]
            num_asistentes = int(random.uniform(1.0 - variacion, 1.0 + variacion) * cupo_sesion)
            candidatos = [s for s in socios_activos if s['id'] not in socios_reservados_hoy]
            if not candidatos: continue

            muestra = min(num_asistentes, len(candidatos))
            asistentes_hoy = random.sample(candidatos, muestra)

            inicio_sesion_global = (dia_idx * MINUTOS_MAXIMOS_POR_DIA) + (sesion * DURACION_SESION)

            for datos_socio in asistentes_hoy:
                socios_reservados_hoy.add(datos_socio['id'])
                llegada = inicio_sesion_global + random.uniform(0, 10)
                fin = llegada + random.randint(60, 90)
                perfil = PerfilGenerado(datos_socio["perfil"])

                usuario = Usuario(
                    id_usuario=datos_socio["id"], nombre=datos_socio["nombre"], tipo_usuario="Socio",
                    tiempo_llegada=llegada, hora_fin=fin, ocupado=False,
                    rutina=datos_socio["rutina"], perfil=perfil, problema=None,
                    config=CONFIG,
                    env=env, gimnasio=gimnasio,
                    faltas_consecutivas=datos_socio["faltas_consecutivas"]
                )
                usuario.satisfaccion = datos_socio.get("satisfaccion_acumulada", 100)
                usuarios_programados.append(usuario)

    return usuarios_programados


def controlador_de_llegadas(env, lista_usuarios, admin_logs):
    lista_usuarios.sort(key=lambda u: u.tiempo_llegada)
    for usuario in lista_usuarios:
        tiempo_a_esperar = usuario.tiempo_llegada - env.now
        if tiempo_a_esperar > 0: yield env.timeout(tiempo_a_esperar)

        dia_actual_idx = int(env.now // MINUTOS_MAXIMOS_POR_DIA)
        if dia_actual_idx >= len(DIAS_SEMANA): break
        nombre_dia = DIAS_SEMANA[dia_actual_idx]
        minuto_del_dia = env.now % MINUTOS_MAXIMOS_POR_DIA
        sesion_del_dia = int(minuto_del_dia // DURACION_SESION)

        usuario.logger_sesion = admin_logs
        usuario.dia_sesion = nombre_dia
        usuario.numero_sesion = sesion_del_dia + 1

        admin_logs.log(f"➕ {usuario.nombre} entra", "LLEGADA")
        admin_logs.registrar_datos({
            "tiempo_simulacion": f"{env.now:.2f}", "tipo_evento": "LLEGADA",
            "id_usuario": usuario.id, "nombre": usuario.nombre, "dia": nombre_dia,
            "sesion": sesion_del_dia + 1, "satisfaccion_actual": usuario.satisfaccion,
            "satisfaccion_inicio": usuario.satisfaccion
        })

        usuario.process = env.process(usuario.entrenar(tiempo_total=90))


def gestor_semanal(env, admin_logs):
    for dia in DIAS_SEMANA:
        num_sesiones = obtener_sesiones_por_dia(dia)
        for i in range(1, num_sesiones + 1):
            admin_logs.cambiar_sesion(dia, i)
            admin_logs.log(f"🔔 INICIO SESIÓN {i} - {dia}", "SESION")
            yield env.timeout(DURACION_SESION)
            admin_logs.log(f"🔕 FIN SESIÓN {i}", "SESION")

        restante = (MINUTOS_MAXIMOS_POR_DIA - num_sesiones * DURACION_SESION)
        if restante > 0: yield env.timeout(restante)


def generar_conclusiones_semanales(lista_visitas, carpeta_destino, mes, semana_relativa, semana_absoluta, socios_db):
    ruta_json = f"{carpeta_destino}/Reporte_INTEGRAL_{mes}_S{semana_relativa}.json"
    ruta_txt = f"{carpeta_destino}/Resumen_Ejecutivo_{mes}_S{semana_relativa}.txt"

    ultima_satisfaccion_map = {}
    satisfaccion_total = 0

    for u in lista_visitas:
        satisfaccion_total += u.satisfaccion
        ultima_satisfaccion_map[u.id] = {"satisfaccion": u.satisfaccion, "faltas": u.faltas_consecutivas}

    bajas_esta_semana = 0
    lista_bajas_detalle = []

    idx_mes_actual = INDICE_MESES.get(mes, 0)
    SAT_CONFIG = CONFIG["satisfaccion"]

    for socio in socios_db:
        if socio["id"] in ultima_satisfaccion_map:
            datos = ultima_satisfaccion_map[socio["id"]]
            socio["satisfaccion_acumulada"] = datos["satisfaccion"]
            socio["faltas_consecutivas"] = datos["faltas"]

            if socio["faltas_consecutivas"] >= 3:
                socio["faltas_consecutivas"] = 0
                socio["castigado_hasta_semana_absoluta"] = semana_absoluta + 2

        if socio.get("activo", True):
            mes_alta = socio.get("mes_alta", "Carga_Inicial")
            idx_alta = INDICE_MESES.get(mes_alta, -1)
            antiguedad = idx_mes_actual - idx_alta

            if antiguedad <= 1:
                umbral_baja = SAT_CONFIG["umbral_baja_novato"]
            elif antiguedad <= 4:
                umbral_baja = SAT_CONFIG["umbral_baja_medio"]
            else:
                umbral_baja = SAT_CONFIG["umbral_baja_veterano"]

            if socio["satisfaccion_acumulada"] < umbral_baja:
                socio["activo"] = False
                socio["fecha_baja"] = f"{mes} - S{semana_relativa}"
                bajas_esta_semana += 1
                lista_bajas_detalle.append({
                    "id": socio["id"], "nombre": socio["nombre"],
                    "motivo": f"Insatisfacción (<{umbral_baja})", "antiguedad": f"{antiguedad} meses"
                })
                # print(f"      ❌ BAJA: {socio['nombre']} (Sat: {socio['satisfaccion_acumulada']}) - Antigüedad: {antiguedad} m")

    # Calculamos socios activos finales
    socios_activos_finales = len([s for s in socios_db if s.get("activo", True)])

    with open(CONFIG["rutas"]["archivo_clientes"], "w", encoding="utf-8") as f:
        json.dump(socios_db, f, indent=4, ensure_ascii=False)

    promedio = satisfaccion_total / len(lista_visitas) if lista_visitas else 0

    informe = {
        "periodo": f"{mes} - S{semana_relativa}",
        "kpis": {"visitas": len(lista_visitas), "sat_media": round(promedio, 2), "bajas": bajas_esta_semana},
        "bajas_detalle": lista_bajas_detalle
    }
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(informe, f, indent=4, ensure_ascii=False)

    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(f"=== {mes.upper()} SEMANA {semana_relativa} ===\n")
        f.write(f"Visitas: {len(lista_visitas)}\nSat Media: {promedio:.2f}\nBajas: {bajas_esta_semana}\n")
        f.write(f"Socios Activos: {socios_activos_finales}\n")

    return {
        "mes": mes,
        "visitas": len(lista_visitas),
        "bajas": bajas_esta_semana,
        "satisfaccion": promedio,
        "socios_activos": socios_activos_finales
    }


def generar_informe_anual(historico, carpeta_raiz):
    ruta_anual = f"{carpeta_raiz}/Reporte_ANUAL_FINAL.json"
    total_visitas = sum(h["visitas"] for h in historico)
    total_bajas = sum(h["bajas"] for h in historico)

    desglose_mensual = {}
    for h in historico:
        mes = h["mes"]
        if mes not in desglose_mensual:
            desglose_mensual[mes] = {"visitas": 0, "bajas": 0, "suma_sat": 0, "count": 0, "socios_activos": 0}

        dm = desglose_mensual[mes]
        dm["visitas"] += h["visitas"]
        dm["bajas"] += h["bajas"]
        dm["suma_sat"] += h["satisfaccion"]
        dm["count"] += 1
        dm["socios_activos"] = h["socios_activos"]

    reporte_mensual_final = []

    mes_max_visitas = ("", 0)
    mes_max_bajas = ("", 0)

    print("\n" + "=" * 55)
    print("📊 RESUMEN ESTADÍSTICO ANUAL")
    print("=" * 55)
    print(f"{'MES':<12} | {'VISITAS':<8} | {'BAJAS':<6} | {'SATISFACCIÓN':<12} | {'SOCIOS':<6}")
    print("-" * 60)

    for mes, data in desglose_mensual.items():
        avg = data["suma_sat"] / data["count"] if data["count"] else 0
        socios_finales = data["socios_activos"]

        reporte_mensual_final.append({
            "mes": mes,
            "visitas": data["visitas"],
            "bajas": data["bajas"],
            "sat_promedio": round(avg, 2),
            "socios_activos_fin_mes": socios_finales
        })

        if data["visitas"] > mes_max_visitas[1]: mes_max_visitas = (mes, data["visitas"])
        if data["bajas"] > mes_max_bajas[1]: mes_max_bajas = (mes, data["bajas"])

        print(f"{mes:<12} | {data['visitas']:<8} | {data['bajas']:<6} | {avg:.2f} / 100   | {socios_finales}")

    avg_global = sum(h["satisfaccion"] for h in historico) / len(historico) if historico else 0
    socios_cierre_anio = historico[-1]["socios_activos"] if historico else 0

    print("=" * 60)
    print(f"🏆 TOTAL VISITAS  : {total_visitas}")
    print(f"📉 TOTAL BAJAS    : {total_bajas}")
    print(f"⭐ NOTA MEDIA AÑO : {avg_global:.2f} / 100")
    print(f"👥 SOCIOS FINALES : {socios_cierre_anio}")
    print("-" * 60)
    print(f"📅 Mes más concurrido : {mes_max_visitas[0]} ({mes_max_visitas[1]} visitas)")
    print(f"💔 Mes con más bajas  : {mes_max_bajas[0]} ({mes_max_bajas[1]} bajas)")
    print("=" * 60)

    informe_final = {
        "kpis_globales": {
            "visitas": total_visitas,
            "bajas": total_bajas,
            "sat_media": avg_global,
            "socios_finales": socios_cierre_anio
        },
        "mensual": reporte_mensual_final
    }
    with open(ruta_anual, "w", encoding="utf-8") as f:
        json.dump(informe_final, f, indent=4, ensure_ascii=False)


def main():
    print("🚀 INICIANDO AÑO ACADÉMICO (CONFIG EXTERNA)...")
    carpeta_raiz = CONFIG["rutas"]["carpeta_logs"]
    if os.path.exists(carpeta_raiz): shutil.rmtree(carpeta_raiz)
    os.makedirs(carpeta_raiz)

    archivo_clientes = CONFIG["rutas"]["archivo_clientes"]
    if os.path.exists(archivo_clientes): os.remove(archivo_clientes)

    # 300 socios iniciales (Ahora se lee del CONFIG)
    cant_inicial = CONFIG["simulacion"].get("usuarios_totales_iniciales", 300)
    socios_db = inicializar_base_datos(archivo_clientes, cantidad_inicial=cant_inicial)

    semana_absoluta = 0
    total_bajas_anuales = 0
    historico_global = []

    for config_mes in CALENDARIO_ACADEMICO:
        mes = config_mes["mes"]
        semanas_mes = config_mes["semanas"]
        peso = config_mes["peso_afluencia"]
        abierto = config_mes["abierto"]
        altas = config_mes.get("nuevas_altas_aprox", 0)

        print(f"\n📅 === INICIANDO {mes.upper()} ({semanas_mes} semanas) ===")
        carpeta_mes = f"{carpeta_raiz}/{mes}"
        if not os.path.exists(carpeta_mes): os.makedirs(carpeta_mes)

        if not abierto:
            print(f"   🎄 {mes}: Cerrado.")
            continue

        if altas > 0:
            socios_db = inyectar_socios_nuevos(socios_db, altas, mes)

        for semana in range(1, semanas_mes + 1):
            semana_absoluta += 1
            print(f"   ► Semana {semana}")
            carpeta_semana = f"{carpeta_mes}/Semana_{semana}"
            if not os.path.exists(carpeta_semana): os.makedirs(carpeta_semana)

            env = simpy.Environment()
            admin_logs = AdministradorDeLogs(carpeta_semana=carpeta_semana)

            try:
                mi_gimnasio = Gimnasio()
                mi_gimnasio.cargar_datos_json(CONFIG["rutas"]["archivo_gym"])
                clasificar_maquinas_por_grupo_muscular(mi_gimnasio)
                for m in mi_gimnasio.maquinas: m.iniciar_simulacion(env)
                mi_gimnasio.abrir_gimnasio()

                visitas = generar_flota_semanal_reutilizando(env, mi_gimnasio, socios_db, semana_absoluta, peso)

                if not visitas:
                    print("      ⚠️ No hay visitas programadas.")
                    break

                env.process(controlador_de_llegadas(env, visitas, admin_logs))
                env.process(gestor_semanal(env, admin_logs))
                env.run(until=TIEMPO_SEMANAL_SIMULACION)

                mi_gimnasio.cerrar_gimnasio()

                resumen = generar_conclusiones_semanales(visitas, carpeta_semana, mes, semana, semana_absoluta,
                                                         socios_db)
                historico_global.append(resumen)
                total_bajas_anuales += resumen["bajas"]

            except Exception as e:
                print(f"❌ Error crítico: {e}")
                raise e

    generar_informe_anual(historico_global, carpeta_raiz)
    print(f"\n🎓 AÑO ACADÉMICO FINALIZADO. Bajas: {total_bajas_anuales}")


if __name__ == "__main__":
    main()