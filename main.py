import simpy
import os
import shutil
from Config import Config
from Loggers import AdministradorDeLogs, GeneradorReportes
from GestorSocios import GestorSocios
from MotorSimulacion import MotorSimulacion
from Gimnasio import Gimnasio


def obtener_nombre_carpeta_unica(base_nombre):
    if not os.path.exists(base_nombre): return base_nombre
    contador = 1
    while True:
        nuevo = f"{base_nombre}_{contador}"
        if not os.path.exists(nuevo): return nuevo
        contador += 1


def main():
    print("🚀 INICIANDO AÑO ACADÉMICO (MODULARIZADO)...")

    cfg = Config()
    raiz_logs = obtener_nombre_carpeta_unica(cfg.datos["rutas"]["carpeta_logs"])
    os.makedirs(raiz_logs)
    print(f"📂 Resultados en: '{raiz_logs}'")
    cfg.datos["rutas"]["carpeta_logs"] = raiz_logs

    gestor_socios = GestorSocios(cfg)
    motor = MotorSimulacion(cfg)
    socios_db = gestor_socios.inicializar_db()

    semana_absoluta = 0
    total_bajas = 0
    historico_global = []

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

        altas_reales = 0
        if altas > 0:
            len_antes = len(socios_db)
            socios_db = gestor_socios.inyectar_nuevos(socios_db, altas, mes)
            altas_reales = len(socios_db) - len_antes

        for s in range(1, semanas + 1):
            semana_absoluta += 1
            print(f"   ► Semana {s}")
            carpeta_sem = f"{carpeta_mes}/Semana_{s}"
            if not os.path.exists(carpeta_sem): os.makedirs(carpeta_sem)

            env = simpy.Environment()
            admin_logs = AdministradorDeLogs(carpeta_sem)

            try:
                gym = Gimnasio()
                gym.cargar_datos_json(cfg.datos["rutas"]["archivo_gym"])
                motor.clasificar_maquinas(gym)
                for m in gym.maquinas: m.iniciar_simulacion(env)
                gym.abrir_gimnasio()

                # --- AHORA RECIBIMOS DOS LISTAS: ASISTENTES Y NO-SHOWS ---
                visitas, no_shows = motor.generar_flota_semanal(env, gym, socios_db, semana_absoluta, peso)

                if not visitas and not no_shows:
                    print("      ⚠️ Sin actividad.")
                    break

                env.process(motor.controlador_llegadas(env, visitas, admin_logs))
                env.process(motor.gestor_semanal(env, admin_logs))

                env.run(until=cfg.TIEMPO_SEMANAL_SIMULACION)
                gym.cerrar_gimnasio()

                altas_reporte = altas_reales if s == 1 else 0

                # --- PASAMOS LA LISTA DE NO-SHOWS AL REPORTE PARA CASTIGAR ---
                resumen = GeneradorReportes.generar_conclusiones_semanales(
                    visitas, no_shows, carpeta_sem, mes, s, semana_absoluta, socios_db, cfg, altas_reporte
                )
                historico_global.append(resumen)
                total_bajas += resumen["bajas"]

            except Exception as e:
                print(f"❌ Error en simulacion: {e}")
                raise e

    GeneradorReportes.generar_informe_anual(historico_global, raiz_logs)
    print(f"\n🎓 FIN DEL AÑO. Bajas Totales: {total_bajas}")
    print(f"📁 Resultados guardados en: {raiz_logs}")


if __name__ == "__main__":
    main()