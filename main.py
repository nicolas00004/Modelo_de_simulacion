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


# --- IMPORTANTE: Si tienes un archivo Monitor.py, descomenta esto y borra la clase de abajo ---
# from Monitor import Monitor

# --- CLASE MONITOR (Por si acaso no la tienes a mano) ---
class Monitor:
    def __init__(self, env, id_monitor, nombre, especialidad):
        self.env = env
        self.id = id_monitor
        self.nombre = nombre
        self.especialidad = especialidad
        # Recurso: El monitor es como una máquina, atiende a 1 persona a la vez
        self.cola = []  # Para gestión visual
        self.resource = simpy.Resource(env, capacity=1)

    def preguntar(self, usuario):
        """Simula el proceso de atender una duda."""
        with self.resource.request() as req:
            # Entra en la cola (visual)
            self.cola.append(usuario)
            yield req
            # Sale de la cola y es atendido
            self.cola.remove(usuario)

            # Tiempo de la duda (2 a 5 minutos)
            tiempo_atencion = random.randint(2, 5)
            yield self.env.timeout(tiempo_atencion)


# --- 1. CLASE LOGS ---
class Logs:
    def __init__(self, ruta_completa_sin_ext):
        carpeta = os.path.dirname(ruta_completa_sin_ext)
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)

        self.archivo_log = f"{ruta_completa_sin_ext}.log"
        self.archivo_csv = f"{ruta_completa_sin_ext}.csv"

        with open(self.archivo_log, "w", encoding="utf-8") as f:
            f.write(f"--- Log iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

        self.cabeceras_escritas = False
        self.fieldnames = [
            "tiempo_simulacion", "tipo_evento", "id_usuario", "nombre",
            "dia", "sesion", "satisfaccion_actual", "satisfaccion_inicio",
            "maquina", "duracion", "cola_tamano", "extra_info"
        ]

        with open(self.archivo_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def _obtener_tiempo(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, mensaje, nivel="INFO"):
        linea = f"[{self._obtener_tiempo()}] [{nivel}] {mensaje}\n"
        with open(self.archivo_log, "a", encoding="utf-8") as f:
            f.write(linea)

    def registrar_datos(self, datos):
        try:
            datos_filtrados = {k: v for k, v in datos.items() if k in self.fieldnames}
            with open(self.archivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(datos_filtrados)
        except Exception as e:
            self.log(f"Error CSV: {e}", "ERROR")

    def cerrar_log_con_resumen(self, reservados, asistentes, monitor_nombre):
        no_presentados = reservados - asistentes
        porcentaje = (asistentes / reservados * 100) if reservados > 0 else 0
        resumen = (
            f"\n----------------------------------------\n"
            f"📊 RESUMEN DE SESIÓN\n"
            f"👮 Monitor de turno : {monitor_nombre}\n"
            f"📅 Reservas Totales : {reservados}\n"
            f"✅ Asistentes Reales: {asistentes}\n"
            f"❌ No Presentados   : {no_presentados}\n"
            f"📈 Tasa Asistencia  : {porcentaje:.1f}%\n"
            f"----------------------------------------\n"
        )
        with open(self.archivo_log, "a", encoding="utf-8") as f:
            f.write(resumen)


# --- 2. ADMINISTRADOR DE LOGS ---
class AdministradorDeLogs:
    def __init__(self, carpeta_semana):
        self.logger_actual = None
        self.carpeta_semana = carpeta_semana
        self.contador_asistentes = 0

    def cambiar_sesion(self, nombre_dia, numero_sesion):
        ruta_base = f"{self.carpeta_semana}/{nombre_dia}/Sesion_{numero_sesion}"
        self.logger_actual = Logs(ruta_base)
        self.contador_asistentes = 0

    def iniciar_log_general(self):
        ruta_base = f"{self.carpeta_semana}/Log_Resumen_Semana"
        self.logger_actual = Logs(ruta_base)

    def log(self, mensaje, nivel="INFO"):
        if self.logger_actual: self.logger_actual.log(mensaje, nivel)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)

    def registrar_entrada_usuario(self):
        self.contador_asistentes += 1

    def finalizar_sesion_actual(self, total_reservados, monitor_nombre):
        if self.logger_actual:
            self.logger_actual.cerrar_log_con_resumen(total_reservados, self.contador_asistentes, monitor_nombre)


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


# --- CONFIGURACIÓN DE PERSONAL (MONITORES) ---
STAFF_INVIERNO = [
    {"id": "M01", "nombre": "Carlos (Turno A)", "especialidad": "Musculación"},
    {"id": "M02", "nombre": "Ana (Turno A)", "especialidad": "Pilates"},
    {"id": "M03", "nombre": "Luis (Turno A)", "especialidad": "Crossfit"},
    {"id": "M04", "nombre": "Laura (Turno A)", "especialidad": "Cardio"}
]

STAFF_PRIMAVERA = [
    {"id": "M05", "nombre": "Pedro (Turno B)", "especialidad": "Powerlifting"},
    {"id": "M06", "nombre": "Sofia (Turno B)", "especialidad": "Yoga"},
    {"id": "M07", "nombre": "Miguel (Turno B)", "especialidad": "Funcional"},
    {"id": "M08", "nombre": "Elena (Turno B)", "especialidad": "Zumba"}
]

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

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
DURACION_SESION = 90
CLIENTES_BASE_POR_SESION = 50


def obtener_sesiones_por_dia(dia):
    if dia == "Sábado": return 4
    return 9


SESIONES_MAXIMAS_DIARIAS = 9
MINUTOS_MAXIMOS_POR_DIA = SESIONES_MAXIMAS_DIARIAS * DURACION_SESION
TIEMPO_SEMANAL_SIMULACION = MINUTOS_MAXIMOS_POR_DIA * len(DIAS_SEMANA)

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


def generar_lote_socios(cantidad, id_inicial, mes_origen):
    lote = []
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
            es_baja_historica = random.random() < 0.10

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
            "mes_alta": mes_origen,
            "rutina": rutina, "perfil": perfil,
            "satisfaccion_acumulada": satisfaccion, "activo": activo,
            "faltas_consecutivas": 0, "castigado_hasta_semana_absoluta": 0,
            "fecha_baja": fecha_baja
        }
        lote.append(socio)
    return lote


def inicializar_base_datos(archivo="datos_clientes.json", cantidad_inicial=300):
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
    with open("datos_clientes.json", "w", encoding="utf-8") as f:
        json.dump(socios_actuales, f, indent=4, ensure_ascii=False)
    return socios_actuales


def generar_flota_semanal_reutilizando(env, gimnasio, base_datos_socios, semana_absoluta, factor_afluencia):
    usuarios_programados = []

    socios_activos = [s for s in base_datos_socios if
                      s.get("activo", True) and s.get("castigado_hasta_semana_absoluta", 0) < semana_absoluta]
    cupo_sesion = int(CLIENTES_BASE_POR_SESION * factor_afluencia)
    print(f"   ℹ️ Socios activos DB: {len(socios_activos)} | Cupo: ~{cupo_sesion} pax/sesión")

    if not socios_activos: return []

    for dia_idx, nombre_dia in enumerate(DIAS_SEMANA):
        num_sesiones = obtener_sesiones_por_dia(nombre_dia)
        socios_reservados_hoy = set()

        for sesion in range(num_sesiones):
            num_asistentes = int(random.uniform(0.6, 1.0) * cupo_sesion)
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

        admin_logs.registrar_entrada_usuario()
        usuario.process = env.process(usuario.entrenar(tiempo_total=90))


def gestor_semanal(env, admin_logs, lista_visitas, mi_gimnasio, equipo_monitores):
    """
    Controla el reloj y asigna el monitor correspondiente (UNO SOLO) por sesión.
    """
    for dia in DIAS_SEMANA:
        num_sesiones = obtener_sesiones_por_dia(dia)
        print(f"   📅 {dia} ({num_sesiones} sesiones)...")

        for i in range(1, num_sesiones + 1):
            admin_logs.cambiar_sesion(dia, i)

            # --- ASIGNACIÓN DE MONITOR ÚNICO PARA ESTA SESIÓN ---
            # Rotamos los 4 monitores del equipo: 1, 2, 3, 4, 1, 2...
            datos_monitor = equipo_monitores[(i - 1) % 4]
            monitor_activo = Monitor(env, datos_monitor["id"], datos_monitor["nombre"], datos_monitor["especialidad"])

            # ¡IMPORTANTE! Asignamos una lista con UN SOLO monitor al gimnasio
            mi_gimnasio.monitores = [monitor_activo]

            admin_logs.log(f"🔔 INICIO SESIÓN {i} - {dia} (Monitor: {monitor_activo.nombre})", "SESION")

            # Calcular reservas para el reporte
            min_inicio_dia = DIAS_SEMANA.index(dia) * MINUTOS_MAXIMOS_POR_DIA
            t_inicio = min_inicio_dia + ((i - 1) * DURACION_SESION)
            t_fin = t_inicio + DURACION_SESION
            reservas_sesion = len([u for u in lista_visitas if t_inicio <= u.tiempo_llegada < t_fin])

            yield env.timeout(DURACION_SESION)

            admin_logs.log(f"🔕 FIN SESIÓN {i}", "SESION")
            admin_logs.finalizar_sesion_actual(reservas_sesion, monitor_activo.nombre)

        restante = (SESIONES_MAXIMAS_DIARIAS - num_sesiones) * DURACION_SESION
        if restante > 0: yield env.timeout(restante)


def generar_conclusiones_semanales(lista_visitas, carpeta_destino, mes, semana_relativa, semana_absoluta, socios_db):
    ruta = f"{carpeta_destino}/Reporte_{mes}_Semana_{semana_relativa}.json"
    ultima_satisfaccion_map = {}
    satisfaccion_total = 0
    resultados = []

    for u in lista_visitas:
        resultados.append({"id": u.id, "satisfaccion_final": u.satisfaccion})
        satisfaccion_total += u.satisfaccion
        ultima_satisfaccion_map[u.id] = {"satisfaccion": u.satisfaccion, "faltas": u.faltas_consecutivas}

    bajas = 0
    lista_bajas = []

    for socio in socios_db:
        if socio["id"] in ultima_satisfaccion_map:
            datos = ultima_satisfaccion_map[socio["id"]]
            socio["satisfaccion_acumulada"] = datos["satisfaccion"]
            socio["faltas_consecutivas"] = datos["faltas"]

            if socio["faltas_consecutivas"] >= 3:
                socio["faltas_consecutivas"] = 0
                socio["castigado_hasta_semana_absoluta"] = semana_absoluta + 1

            if socio["satisfaccion_acumulada"] < 20 and socio.get("activo", True):
                socio["activo"] = False
                socio["fecha_baja"] = f"{mes} - Semana {semana_relativa}"
                bajas += 1
                lista_bajas.append({"id": socio["id"], "nombre": socio["nombre"], "motivo": "Insatisfacción"})
                print(f"      ❌ BAJA: {socio['nombre']}")

    promedio = satisfaccion_total / len(lista_visitas) if lista_visitas else 0

    informe = {
        "periodo": f"{mes} - Semana {semana_relativa}",
        "resumen": {"visitas": len(lista_visitas), "satisfaccion_media": round(promedio, 2), "bajas": bajas},
        "bajas_detalle": lista_bajas
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(informe, f, indent=4, ensure_ascii=False)
    with open("datos_clientes.json", "w", encoding="utf-8") as f:
        json.dump(socios_db, f, indent=4, ensure_ascii=False)

    return bajas


def main():
    print("🚀 INICIANDO AÑO ACADÉMICO (SEP - JUN)...")
    carpeta_raiz = "logs_anuales"
    if os.path.exists(carpeta_raiz): shutil.rmtree(carpeta_raiz)
    os.makedirs(carpeta_raiz)

    if os.path.exists("datos_clientes.json"): os.remove("datos_clientes.json")
    socios_db = inicializar_base_datos("datos_clientes.json", cantidad_inicial=300)

    semana_absoluta = 0
    total_bajas_anuales = 0

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

        # --- SELECCIÓN DEL EQUIPO DE MONITORES SEGÚN LA ÉPOCA ---
        meses_invierno = ["Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero"]
        equipo_monitores = STAFF_INVIERNO if mes in meses_invierno else STAFF_PRIMAVERA
        print(f"   👮 Equipo de Monitores: {'Invierno' if mes in meses_invierno else 'Primavera'}")

        for semana in range(1, semanas_mes + 1):
            semana_absoluta += 1
            print(f"   ► Semana {semana}")
            carpeta_semana = f"{carpeta_mes}/Semana_{semana}"
            if not os.path.exists(carpeta_semana): os.makedirs(carpeta_semana)

            env = simpy.Environment()
            admin_logs = AdministradorDeLogs(carpeta_semana=carpeta_semana)
            admin_logs.iniciar_log_general()

            try:
                mi_gimnasio = Gimnasio()
                mi_gimnasio.cargar_datos_json("datos_gimnasio.json")
                clasificar_maquinas_por_grupo_muscular(mi_gimnasio)
                for m in mi_gimnasio.maquinas: m.iniciar_simulacion(env)
                mi_gimnasio.abrir_gimnasio()

                visitas = generar_flota_semanal_reutilizando(env, mi_gimnasio, socios_db, semana_absoluta, peso)

                if not visitas:
                    print("      ⚠️ No hay visitas programadas.")
                    break

                env.process(controlador_de_llegadas(env, visitas, admin_logs))

                # --- PASAMOS EL EQUIPO DE MONITORES CORRECTO AL GESTOR ---
                env.process(gestor_semanal(env, admin_logs, visitas, mi_gimnasio, equipo_monitores))

                env.run(until=TIEMPO_SEMANAL_SIMULACION)

                mi_gimnasio.cerrar_gimnasio()
                bajas = generar_conclusiones_semanales(visitas, carpeta_semana, mes, semana, semana_absoluta, socios_db)
                total_bajas_anuales += bajas

            except Exception as e:
                print(f"❌ Error crítico: {e}")
                raise e

    print(f"\n🎓 AÑO ACADÉMICO FINALIZADO.")
    print(f"📉 Total Bajas: {total_bajas_anuales}")
    print(f"📂 Resultados en '{carpeta_raiz}'")


if __name__ == "__main__":
    main()