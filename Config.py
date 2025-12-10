import json
import os


class Config:
    def __init__(self, archivo_json="config.json"):
        self.datos = self._cargar_configuracion(archivo_json)

        # Constantes derivadas
        self.DURACION_SESION = self.datos["simulacion"]["duracion_sesion_minutos"]
        self.CLIENTES_BASE = self.datos["simulacion"]["clientes_base_por_sesion"]
        self.SESIONES_DIA_LABORAL = 9
        self.SESIONES_SABADO = 4
        self.MINUTOS_MAXIMOS_POR_DIA = 9 * self.DURACION_SESION
        self.TIEMPO_SEMANAL_SIMULACION = self.MINUTOS_MAXIMOS_POR_DIA * 6

        # Calendario
        self.CALENDARIO_ACADEMICO = [
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

        self.INDICE_MESES = {m["mes"]: i for i, m in enumerate(self.CALENDARIO_ACADEMICO) if m["mes"] != "Navidad"}
        self.INDICE_MESES["Carga_Inicial"] = -1
        self.DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

    def _cargar_configuracion(self, archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Config no encontrada, usando valores por defecto.")
            return {
                "simulacion": {"duracion_sesion_minutos": 90, "clientes_base_por_sesion": 50,
                               "probabilidad_baja_historica": 0.15, "variacion_afluencia": 0.2,
                               "usuarios_totales_iniciales": 300},
                "satisfaccion": {"umbral_baja_novato": 40, "umbral_baja_medio": 25, "umbral_baja_veterano": 10,
                                 "penalizacion_espera_cola": 0.5},
                "rutas": {"archivo_clientes": "datos_clientes.json", "archivo_gym": "datos_gimnasio.json",
                          "carpeta_logs": "logs_anuales"}
            }

    def obtener_sesiones_por_dia(self, dia):
        return self.SESIONES_SABADO if dia == "Sábado" else self.SESIONES_DIA_LABORAL