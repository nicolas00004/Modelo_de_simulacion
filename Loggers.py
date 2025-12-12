import os
import csv
import json
from datetime import datetime
import random


class Logs:
    def __init__(self, ruta_completa_sin_ext):
        carpeta = os.path.dirname(ruta_completa_sin_ext)
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)

        self.archivo_txt = f"{ruta_completa_sin_ext}.txt"
        self.archivo_csv = f"{ruta_completa_sin_ext}.csv"

        with open(self.archivo_txt, "w", encoding="utf-8") as f:
            f.write(f"--- Sesión Iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

        self.fieldnames = [
            "tiempo_simulacion", "tipo_evento", "id_usuario", "nombre",
            "dia", "sesion", "satisfaccion_actual",
            "balance_economico", "maquinas_rotas_count",
            "maquina", "duracion", "extra_info"
        ]
        with open(self.archivo_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def log(self, mensaje):
        """Escribe el mensaje directamente, sin metadatos INFO."""
        with open(self.archivo_txt, "a", encoding="utf-8") as f:
            f.write(f"{mensaje}\n")

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
        self.asistentes_reales = 0

    def cambiar_sesion(self, nombre_dia, numero_sesion):
        ruta_base = f"{self.carpeta_semana}/{nombre_dia}/Sesion_{numero_sesion}"
        self.logger_actual = Logs(ruta_base)
        self.asistentes_reales = 0

    def finalizar_sesion(self):
        if self.logger_actual:
            self.logger_actual.log(f"Fin de sesión. Asistentes: {self.asistentes_reales}")

    def registrar_entrada_usuario(self):
        self.asistentes_reales += 1

    def log(self, mensaje):
        if self.logger_actual: self.logger_actual.log(mensaje)

    def registrar_datos(self, datos):
        if self.logger_actual: self.logger_actual.registrar_datos(datos)


class GeneradorReportes:
    @staticmethod
    def generar_conclusiones_semanales(lista_visitas, ids_no_shows, carpeta_destino, mes, semana_relativa,
                                       semana_absoluta, socios_db, config, nuevas_altas, gym_obj):
        """Procesa satisfacción, ejecuta bajas y guarda reporte JSON."""

        # Actualizar satisfacción en la base de datos de los que asistieron
        visitas_map = {u.id: u.satisfaccion for u in lista_visitas}

        bajas_esta_semana = 0
        bajas_detalle = {"Novato": 0, "Medio": 0, "Veterano": 0}

        SAT_CFG = config.datos["satisfaccion"]
        prob_perdon = config.datos["simulacion"].get("probabilidad_reconsiderar_baja", 0.3)

        # Evaluar a todos los socios activos para ver quién se da de baja
        for socio in socios_db:
            if not socio.get("activo", True): continue

            # Si vino esta semana, actualizamos su humor acumulado
            if socio["id"] in visitas_map:
                socio["satisfaccion_acumulada"] = visitas_map[socio["id"]]

            # Lógica de antigüedad para el umbral de baja
            idx_actual = config.INDICE_MESES.get(mes, 0)
            idx_alta = config.INDICE_MESES.get(socio.get("mes_alta", mes), 0)
            antiguedad = max(0, idx_actual - idx_alta)

            if antiguedad <= 1:
                tipo, umbral = "Novato", SAT_CFG["umbral_baja_novato"]
            elif antiguedad <= 4:
                tipo, umbral = "Medio", SAT_CFG["umbral_baja_medio"]
            else:
                tipo, umbral = "Veterano", SAT_CFG["umbral_baja_veterano"]

            # Decisión de Baja
            if socio["satisfaccion_acumulada"] < umbral:
                if random.random() > prob_perdon:
                    socio["activo"] = False
                    socio["fecha_baja"] = f"{mes} - S{semana_relativa}"
                    bajas_esta_semana += 1
                    bajas_detalle[tipo] += 1

        # Contar distribución por tipo para el gráfico de tarta
        activos_lista = [s for s in socios_db if s.get("activo", True)]
        conteo_tipos = {"Estudiante": 0, "Trabajador": 0, "Egresado": 0}
        for s in activos_lista:
            t = s.get("subtipo", "Estudiante")
            if t in conteo_tipos: conteo_tipos[t] += 1

        # Crear y Guardar el JSON Integral
        reporte_semanal = {
            "mes": mes,
            "semana": semana_relativa,
            "asistentes": len(lista_visitas),
            "bajas": bajas_esta_semana,
            "satisfaccion": round(sum(u.satisfaccion for u in lista_visitas) / len(lista_visitas),
                                  2) if lista_visitas else 0,
            "socios_activos": len(activos_lista),
            "ingresos_mes": round(gym_obj.balance, 2),
            "gastos_mes": round(gym_obj.costes_reparacion_acumulados, 2),
            "distribucion_socios": conteo_tipos
        }

        ruta_json = f"{carpeta_destino}/Reporte_INTEGRAL_{mes}_S{semana_relativa}.json"
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(reporte_semanal, f, indent=4)

        # Notificar por consola
        if bajas_esta_semana > 0:
            print(
                f"      📉 BAJAS: -{bajas_esta_semana} socios ({bajas_detalle['Novato']} Nov, {bajas_detalle['Medio']} Med, {bajas_detalle['Veterano']} Vet)")

        return reporte_semanal

    @staticmethod
    def generar_informe_anual(historico, carpeta_raiz, balance_final=0, beneficio_neto=0):
        resumen = {
            "total_visitas": sum(h["asistentes"] for h in historico),
            "total_bajas": sum(h["bajas"] for h in historico),
            "balance_final": balance_final,
            "beneficio_neto": beneficio_neto,
            "historico_detallado": historico
        }
        ruta_final = f"{carpeta_raiz}/Reporte_ANUAL_FINAL.json"
        with open(ruta_final, "w", encoding="utf-8") as f:
            json.dump(resumen, f, indent=4)
        print(f"\n✅ Informe anual consolidado en: {ruta_final}")