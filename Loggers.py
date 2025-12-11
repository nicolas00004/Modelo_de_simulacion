import os
import csv
import json
import random  # Necesario para la probabilidad de segunda oportunidad
from datetime import datetime
from collections import Counter


class Logs:
    def __init__(self, ruta_completa_sin_ext):
        carpeta = os.path.dirname(ruta_completa_sin_ext)
        if not os.path.exists(carpeta): os.makedirs(carpeta)
        self.archivo_txt = f"{ruta_completa_sin_ext}.txt"
        self.archivo_csv = f"{ruta_completa_sin_ext}.csv"
        with open(self.archivo_txt, "w", encoding="utf-8") as f:
            f.write(f"--- Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        self.fieldnames = ["tiempo_simulacion", "tipo_evento", "id_usuario", "nombre", "dia", "sesion",
                           "satisfaccion_actual", "satisfaccion_inicio", "maquina", "duracion", "cola_tamano",
                           "extra_info"]
        with open(self.archivo_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def log(self, mensaje, nivel="INFO"):
        with open(self.archivo_txt, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{nivel}] {mensaje}\n")

    def registrar_datos(self, datos):
        try:
            datos_filtrados = {k: v for k, v in datos.items() if k in self.fieldnames}
            with open(self.archivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(datos_filtrados)
        except:
            pass

    def cerrar_con_resumen(self, reservados, asistentes):
        with open(self.archivo_txt, "a", encoding="utf-8") as f:
            f.write(f"\n--- RESUMEN ---\nReservas: {reservados} | Asistentes: {asistentes}\n")


class AdministradorDeLogs:
    def __init__(self, carpeta_semana):
        self.logger_actual = None
        self.carpeta_semana = carpeta_semana
        self.contador_asistentes = 0

    def cambiar_sesion(self, nombre_dia, numero_sesion):
        # MODO LIMPIO (Si quieres logs detallados descomenta la linea de abajo)
        # self.logger_actual = Logs(f"{self.carpeta_semana}/{nombre_dia}/Sesion_{numero_sesion}")
        self.logger_actual = None
        self.contador_asistentes = 0

    def registrar_entrada_usuario(self):
        self.contador_asistentes += 1

    def finalizar_sesion_actual(self, total_reservados):
        if self.logger_actual: self.logger_actual.cerrar_con_resumen(total_reservados, self.contador_asistentes)

    def log(self, mensaje, nivel="INFO"):
        if self.logger_actual: self.logger_actual.log(mensaje, nivel)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)


# --- LÓGICA DE REPORTES ---
class GeneradorReportes:
    @staticmethod
    def generar_conclusiones_semanales(lista_visitas, ids_no_shows, carpeta_destino, mes, semana_relativa,
                                       semana_absoluta, socios_db, config, nuevas_altas):
        ruta_json = f"{carpeta_destino}/Reporte_INTEGRAL_{mes}_S{semana_relativa}.json"
        ruta_txt = f"{carpeta_destino}/Resumen_Ejecutivo_{mes}_S{semana_relativa}.txt"

        ultima_satisfaccion_map = {u.id: u.satisfaccion for u in lista_visitas}

        bajas = 0
        lista_bajas = []
        castigados_nuevos = 0
        perdonados = 0

        idx_mes_actual = config.INDICE_MESES.get(mes, 0)
        SAT_CONFIG = config.datos["satisfaccion"]
        prob_perdon = config.datos["simulacion"].get("probabilidad_reconsiderar_baja", 0.0)

        conteo_no_shows = Counter(ids_no_shows)

        for socio in socios_db:
            sid = socio["id"]

            # 1. ACTUALIZAR SATISFACCIÓN
            if sid in ultima_satisfaccion_map:
                socio["satisfaccion_acumulada"] = ultima_satisfaccion_map[sid]
                socio["faltas_consecutivas"] = 0

            # 2. GESTIONAR FALTAS
            faltas_esta_semana = conteo_no_shows.get(sid, 0)
            if faltas_esta_semana > 0:
                socio["faltas_consecutivas"] += faltas_esta_semana

            # 3. APLICAR CASTIGO
            if socio["faltas_consecutivas"] >= 3 and socio.get("castigado_hasta_semana_absoluta", 0) <= semana_absoluta:
                socio["faltas_consecutivas"] = 0
                socio["castigado_hasta_semana_absoluta"] = semana_absoluta + 2
                castigados_nuevos += 1

            # 4. GESTIÓN DE BAJAS Y SEGUNDA OPORTUNIDAD
            if socio.get("activo", True):
                mes_alta = socio.get("mes_alta", "Carga_Inicial")
                idx_alta = config.INDICE_MESES.get(mes_alta, -1)
                antiguedad = idx_mes_actual - idx_alta

                if antiguedad <= 1:
                    umbral = SAT_CONFIG["umbral_baja_novato"]
                elif antiguedad <= 4:
                    umbral = SAT_CONFIG["umbral_baja_medio"]
                else:
                    umbral = SAT_CONFIG["umbral_baja_veterano"]

                if socio["satisfaccion_acumulada"] < umbral:
                    # --- AQUÍ ESTÁ EL CAMBIO: Segunda Oportunidad ---
                    if random.random() < prob_perdon:
                        # SE SALVA
                        perdonados += 1
                        socio[
                            "satisfaccion_acumulada"] = 55  # Le subimos un poco el ánimo para que no caiga la semana que viene
                        print(
                            f"      😅 {socio['nombre']} pensó en irse (Sat {socio['satisfaccion_acumulada']}), pero le dará otra oportunidad.")
                    else:
                        # SE VA DEFINITIVAMENTE
                        socio["activo"] = False
                        socio["fecha_baja"] = f"{mes} - S{semana_relativa}"
                        bajas += 1
                        lista_bajas.append({"id": sid, "motivo": f"Sat < {umbral}"})
                        print(
                            f"      ❌ BAJA: {socio['nombre']} (Sat: {socio['satisfaccion_acumulada']}) - Antigüedad: {antiguedad} m")

        with open(config.datos["rutas"]["archivo_clientes"], "w", encoding="utf-8") as f:
            json.dump(socios_db, f, indent=4, ensure_ascii=False)

        promedio = sum(ultima_satisfaccion_map.values()) / len(
            ultima_satisfaccion_map) if ultima_satisfaccion_map else 0
        socios_activos = len([s for s in socios_db if s.get("activo", True)])

        informe = {
            "periodo": f"{mes} - S{semana_relativa}",
            "kpis": {
                "visitas": len(lista_visitas),
                "sat_media": round(promedio, 2),
                "bajas": bajas,
                "perdonados_segunda_oportunidad": perdonados,
                "socios_activos": socios_activos,
                "nuevas_altas": nuevas_altas,
                "nuevos_castigados": castigados_nuevos
            },
            "bajas_detalle": lista_bajas
        }
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(informe, f, indent=4)

        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(f"=== {mes.upper()} S{semana_relativa} ===\n")
            f.write(f"Visitas: {len(lista_visitas)}\nSat Media: {promedio:.2f}\n")
            f.write(f"Bajas: {bajas}\nSalvados in extremis: {perdonados}\n")

        return {"mes": mes, "visitas": len(lista_visitas), "bajas": bajas, "altas": nuevas_altas,
                "satisfaccion": promedio, "socios_activos": socios_activos}

    @staticmethod
    def generar_informe_anual(historico, carpeta_raiz):
        ruta_anual = f"{carpeta_raiz}/Reporte_ANUAL_FINAL.json"
        total_visitas = sum(h["visitas"] for h in historico)
        total_bajas = sum(h["bajas"] for h in historico)
        total_altas = sum(h["altas"] for h in historico)

        desglose = {}
        for h in historico:
            mes = h["mes"]
            if mes not in desglose: desglose[mes] = {"visitas": 0, "bajas": 0, "altas": 0, "suma_sat": 0, "count": 0,
                                                     "socios": 0}
            d = desglose[mes]
            d["visitas"] += h["visitas"];
            d["bajas"] += h["bajas"];
            d["altas"] += h["altas"]
            d["suma_sat"] += h["satisfaccion"];
            d["count"] += 1;
            d["socios"] = h["socios_activos"]

        final = []
        print(
            "\n" + "=" * 65 + "\n📊 RESUMEN ANUAL\n" + "=" * 65 + "\nMES | VISITAS | ALTAS | BAJAS | SAT | SOCIOS\n" + "-" * 70)
        for m, d in desglose.items():
            avg = d["suma_sat"] / d["count"] if d["count"] else 0
            final.append(
                {"mes": m, "visitas": d["visitas"], "altas": d["altas"], "bajas": d["bajas"], "sat": round(avg, 2),
                 "socios": d["socios"]})
            print(f"{m:<10} | {d['visitas']:<7} | {d['altas']:<5} | {d['bajas']:<5} | {avg:.2f} | {d['socios']}")

        with open(ruta_anual, "w", encoding="utf-8") as f:
            json.dump(
                {"global": {"visitas": total_visitas, "bajas": total_bajas, "altas": total_altas}, "mensual": final}, f,
                indent=4)