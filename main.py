import simpy
import os
import shutil
from Config import Config
from Loggers import AdministradorDeLogs, GeneradorReportes
from GestorSocios import GestorSocios
from MotorSimulacion import MotorSimulacion
from Gimnasio import Gimnasio


def obtener_nombre_carpeta_unica(base_nombre):
    """
    Busca un nombre de carpeta libre.
    Ej: si 'logs_anuales' existe, devuelve 'logs_anuales_1'.
    """
    if not os.path.exists(base_nombre):
        return base_nombre

    contador = 1
    while True:
        nuevo_nombre = f"{base_nombre}_{contador}"
        if not os.path.exists(nuevo_nombre):
            return nuevo_nombre
        contador += 1


def main():
    print("🚀 INICIANDO AÑO ACADÉMICO (MODULARIZADO)...")

    # 1. Cargar Configuración
    cfg = Config()

    # --- CAMBIO IMPORTANTE: GENERACIÓN DE CARPETA ÚNICA ---
    nombre_base = cfg.datos["rutas"]["carpeta_logs"]
    raiz_logs = obtener_nombre_carpeta_unica(nombre_base)

    os.makedirs(raiz_logs)
    print(f"📂 Los resultados se guardarán en: '{raiz_logs}'")

    # Actualizamos la configuración en memoria para que el resto del programa use la nueva carpeta
    cfg.datos["rutas"]["carpeta_logs"] = raiz_logs
    # ------------------------------------------------------

    # 3. Inicializar Gestores
    gestor_socios = GestorSocios(cfg)
    motor = MotorSimulacion(cfg)
    socios_db = gestor_socios.inicializar_db()

    # Variables de control
    semana_absoluta = 0
    total_bajas = 0
    historico_global = []

    # --- BUCLE ANUAL ---
    for mes_config in cfg.CALENDARIO_ACADEMICO:
        mes = mes_config["mes"]
        semanas = mes_config["semanas"]
        peso = mes_config["peso_afluencia"]
        abierto = mes_config["abierto"]
        altas = mes_config.get("nuevas_altas_aprox", 0)

        print(f"\n📅 === {mes.upper()} ===")
        carpeta_mes = f"{raiz_logs}/{mes}"
        if not os.path.exists(carpeta_mes): os.makedirs(carpeta_mes)

        if not abierto:
            print(f"   🎄 Cerrado.")
            continue

        if altas > 0:
            socios_db = gestor_socios.inyectar_nuevos(socios_db, altas, mes)

        for s in range(1, semanas + 1):
            semana_absoluta += 1
            print(f"   ► Semana {s}")
            carpeta_sem = f"{carpeta_mes}/Semana_{s}"
            if not os.path.exists(carpeta_sem): os.makedirs(carpeta_sem)

            # Preparar Simulación
            env = simpy.Environment()
            admin_logs = AdministradorDeLogs(carpeta_sem)

            try:
                # Cargar Gym
                gym = Gimnasio()
                gym.cargar_datos_json(cfg.datos["rutas"]["archivo_gym"])
                motor.clasificar_maquinas(gym)
                for m in gym.maquinas: m.iniciar_simulacion(env)
                gym.abrir_gimnasio()

                # Generar Usuarios y Procesos
                visitas = motor.generar_flota_semanal(env, gym, socios_db, semana_absoluta, peso)

                if not visitas:
                    print("      ⚠️ Sin visitas.")
                    break

                env.process(motor.controlador_llegadas(env, visitas, admin_logs))
                env.process(motor.gestor_semanal(env, admin_logs))

                # EJECUTAR SIMULACIÓN
                env.run(until=cfg.TIEMPO_SEMANAL_SIMULACION)
                gym.cerrar_gimnasio()

                # Reportes
                resumen = GeneradorReportes.generar_conclusiones_semanales(
                    visitas, carpeta_sem, mes, s, semana_absoluta, socios_db, cfg
                )
                historico_global.append(resumen)
                total_bajas += resumen["bajas"]

            except Exception as e:
                print(f"❌ Error en simulacion: {e}")
                raise e

    # Informe Final
    GeneradorReportes.generar_informe_anual(historico_global, raiz_logs)
    print(f"\n🎓 FIN DEL AÑO. Bajas Totales: {total_bajas}")
    print(f"📁 Resultados guardados en: {raiz_logs}")


if __name__ == "__main__":
    main()