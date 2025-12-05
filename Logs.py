

from datetime import datetime

class Logs:
    def __init__(self, archivo):
        self.archivo = archivo
        # Crea el archivo de log si no existe
        with open(self.archivo, "w", encoding="utf-8") as f:
            f.write(f"--- Log iniciado el {self._obtener_tiempo()} ---\n")

    def _obtener_tiempo(self):
        # Devuelve la fecha y hora actual en formato legible
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, mensaje, nivel="INFO"):
        # Guarda un mensaje en el archivo de log con un nivel de severidad
        linea = f"[{self._obtener_tiempo()}] [{nivel}] {mensaje}\n"
        with open(self.archivo, "a", encoding="utf-8") as f:
            f.write(linea)

    def log_parametros(self, nombre_algoritmo, fichero, semilla, **kwargs):
        """Guarda los parámetros iniciales del experimento."""
        self.log(f"Comenzando ejecución del fichero: {fichero} con el algoritmo: {nombre_algoritmo}", "SETUP")
        self.log(f"  Parámetros del algoritmo", "SETUP")
        self.log(f"  Semilla: {semilla}", "SETUP")
        for k, v in kwargs.items():
            self.log(f"  {k}: {v}", "SETUP")
        self.log("--", "SETUP")




