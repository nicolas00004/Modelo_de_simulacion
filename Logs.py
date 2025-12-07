import csv
import json
import os
from datetime import datetime


class Logs:
    def __init__(self, nombre_base):
        """
        :param nombre_base: Nombre del experimento (ej: "simulacion_01").
                            Se generarán dos archivos: .log y .csv
        """
        # Creamos una carpeta 'logs' para no ensuciar el directorio principal
        if not os.path.exists("logs"):
            os.makedirs("logs")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Archivo 1: Texto para lectura humana (debug)
        self.archivo_log = f"logs/{nombre_base}_{timestamp}.log"

        # Archivo 2: CSV para estadísticas (Excel/Pandas)
        self.archivo_csv = f"logs/{nombre_base}_{timestamp}.csv"

        # Inicializamos el archivo de texto
        with open(self.archivo_log, "w", encoding="utf-8") as f:
            f.write(f"--- Experimento iniciado el {self._obtener_tiempo()} ---\n")

        # Inicializamos el CSV (variables para controlar cabeceras)
        self.cabeceras_escritas = False

    def _obtener_tiempo(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, mensaje, nivel="INFO"):
        """Guarda mensajes de texto (eventos, errores, avisos)."""
        linea = f"[{self._obtener_tiempo()}] [{nivel}] {mensaje}\n"
        print(linea.strip())  # Opcional: imprimir también en consola
        with open(self.archivo_log, "a", encoding="utf-8") as f:
            f.write(linea)

    def log_parametros(self, **kwargs):
        """
        Guarda la configuración inicial.
        Escribe en el .log como texto y guarda un .json separado si es necesario.
        """
        self.log("--- CONFIGURACIÓN DEL EXPERIMENTO ---", "SETUP")
        for k, v in kwargs.items():
            self.log(f"{k}: {v}", "PARAM")
        self.log("-------------------------------------", "SETUP")

        # Opcional: Guardar params en un JSON lateral para reproducibilidad exacta
        archivo_json = self.archivo_log.replace('.log', '_params.json')
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(kwargs, f, indent=4)

    def registrar_datos(self, datos: dict):
        """
        ESTA ES LA FUNCIÓN CLAVE PARA ESTADÍSTICA.
        Recibe un diccionario y lo guarda como una fila en el CSV.
        Ej: datos = {"iteracion": 1, "fitness_promedio": 10.5, "mejor_fitness": 50}
        """
        try:
            with open(self.archivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=datos.keys())

                # Si es la primera vez que escribimos, ponemos los títulos de las columnas
                if not self.cabeceras_escritas:
                    writer.writeheader()
                    self.cabeceras_escritas = True

                # Escribimos la fila de datos
                writer.writerow(datos)

        except Exception as e:
            self.log(f"Error escribiendo en CSV: {e}", "ERROR")