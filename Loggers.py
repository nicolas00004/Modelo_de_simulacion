import os
import csv
import json
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


class AdministradorDeLogs:
    def __init__(self, carpeta_semana):
        self.logger_actual = None
        self.carpeta_semana = carpeta_semana

    def cambiar_sesion(self, nombre_dia, numero_sesion):
        self.logger_actual = None  # MODO LIMPIO

    def log(self, mensaje, nivel="INFO"):
        if self.logger_actual: self.logger_actual.log(mensaje, nivel)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)


# --- LÓGICA DE REPORTES ---
class GeneradorReportes:
    @staticmethod
    def generar_conclusiones_semanales(lista_visitas, carpeta_destino, mes, semana_relativa, semana_absoluta, socios_db,
                                       config):
        ruta_json = f"{carpeta_destino}/Reporte_INTEGRAL_{mes}_S{semana_relativa}.json"
        ruta_txt = f"{carpeta_destino}/Resumen_Ejecutivo_{mes}_S{semana_relativa}.txt"

        ultima_satisfaccion_map = {}
        satisfaccion_total = 0
        for u in lista_visitas:
            satisfaccion_total += u.satisfaccion
            ultima_satisfaccion_map[u.id] = {"satisfaccion": u.satisfaccion, "faltas": u.faltas_consecutivas}

        bajas = 0
        lista_bajas = []
        idx_mes_actual = config.INDICE_MESES.get(mes, 0)
        SAT_CONFIG = config.datos["satisfaccion"]

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
                idx_alta = config.INDICE_MESES.get(mes_alta, -1)
                antiguedad = idx_mes_actual - idx_alta

                if antiguedad <= 1:
                    umbral = SAT_CONFIG["umbral_baja_novato"]
                elif antiguedad <= 4:
                    umbral = SAT_CONFIG["umbral_baja_medio"]
                else:
                    umbral = SAT_CONFIG["umbral_baja_veterano"]

                if socio["satisfaccion_acumulada"] < umbral:
                    socio["activo"] = False
                    socio["fecha_baja"] = f"{mes} - S{semana_relativa}"
                    bajas += 1
                    lista_bajas.append({"id": socio["id"], "motivo": f"Sat < {umbral} (Antig: {antiguedad}m)"})
                    print(f"      ❌ BAJA: {socio['nombre']} (Sat: {socio['satisfaccion_acumulada']})")

        with open(config.datos["rutas"]["archivo_clientes"], "w", encoding="utf-8") as f:
            json.dump(socios_db, f, indent=4, ensure_ascii=False)

        promedio = satisfaccion_total / len(lista_visitas) if lista_visitas else 0
        socios_activos = len([s for s in socios_db if s.get("activo", True)])

        informe = {
            "periodo": f"{mes} - S{semana_relativa}",
            "kpis": {"visitas": len(lista_visitas), "sat_media": round(promedio, 2), "bajas": bajas,
                     "socios_activos": socios_activos},
            "bajas_detalle": lista_bajas
        }
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(informe, f, indent=4)
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(
                f"=== {mes.upper()} S{semana_relativa} ===\nVisitas: {len(lista_visitas)}\nSat Media: {promedio:.2f}\nBajas: {bajas}\nSocios Activos: {socios_activos}")

        return {"mes": mes, "visitas": len(lista_visitas), "bajas": bajas, "satisfaccion": promedio,
                "socios_activos": socios_activos}

    @staticmethod
    def generar_informe_anual(historico, carpeta_raiz):
        ruta_anual = f"{carpeta_raiz}/Reporte_ANUAL_FINAL.json"
        total_visitas = sum(h["visitas"] for h in historico)
        total_bajas = sum(h["bajas"] for h in historico)
        desglose = {}
        for h in historico:
            mes = h["mes"]
            if mes not in desglose: desglose[mes] = {"visitas": 0, "bajas": 0, "suma_sat": 0, "count": 0, "socios": 0}
            d = desglose[mes]
            d["visitas"] += h["visitas"];
            d["bajas"] += h["bajas"];
            d["suma_sat"] += h["satisfaccion"];
            d["count"] += 1;
            d["socios"] = h["socios_activos"]

        final = []
        print(
            "\n" + "=" * 55 + "\n📊 RESUMEN ANUAL\n" + "=" * 55 + "\nMES | VISITAS | BAJAS | SAT | SOCIOS\n" + "-" * 60)
        for m, d in desglose.items():
            avg = d["suma_sat"] / d["count"] if d["count"] else 0
            final.append({"mes": m, "visitas": d["visitas"], "bajas": d["bajas"], "sat": avg, "socios": d["socios"]})
            print(f"{m:<10} | {d['visitas']:<7} | {d['bajas']:<5} | {avg:.2f} | {d['socios']}")

        with open(ruta_anual, "w", encoding="utf-8") as f:
            json.dump({"global": {"visitas": total_visitas, "bajas": total_bajas}, "mensual": final}, f, indent=4)