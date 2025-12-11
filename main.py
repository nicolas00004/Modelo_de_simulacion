import simpy
import os
import shutil
from datetime import datetime, timedelta
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
    print("\n🚀 INICIANDO SIMULACIÓN ANUAL (MODULARIZADO)")
    print("=" * 60)

    cfg = Config()

    raiz_logs = obtener_nombre_carpeta_unica(cfg.datos["rutas"]["carpeta_logs"])
    os.makedirs(raiz_logs)
    print(f"📂 Los resultados se guardarán en: '{raiz_logs}'\n")
    cfg.datos["rutas"]["carpeta_logs"] = raiz_logs

    gestor_socios = GestorSocios(cfg)
    motor = MotorSimulacion(cfg)
    socios_db = gestor_socios.inicializar_db()

    fecha_actual = datetime(2023, 9, 4)

    semana_absoluta = 0
    total_bajas = 0
    historico_global = []

    for mes_config in cfg.CALENDARIO_ACADEMICO:
        mes = mes_config["mes"]
        semanas = mes_config["semanas"]
        peso = mes_config["peso_afluencia"]
        abierto = mes_config["abierto"]
        altas_objetivo = mes_config.get("nuevas_altas_aprox", 0)

        if not abierto: continue

        print(f"\n{'▀' * 60}")
        print(f"📅  {mes.upper()}")
        print(f"{'▄' * 60}")

        carpeta_mes = f"{raiz_logs}/{mes}"
        if not os.path.exists(carpeta_mes): os.makedirs(carpeta_mes)

        altas_reales_este_mes = 0
        if altas_objetivo > 0:
            len_antes = len(socios_db)
            socios_db = gestor_socios.inyectar_nuevos(socios_db, altas_objetivo, mes)
            len_despues = len(socios_db)
            altas_reales_este_mes = len_despues - len_antes

        for s in range(1, semanas + 1):
            semana_absoluta += 1

            fecha_fin_semana = fecha_actual + timedelta(days=6)
            str_rango = f"Del {fecha_actual.strftime('%d/%m')} al {fecha_fin_semana.strftime('%d/%m')}"

            es_vacaciones = False
            motivo = ""

            if mes == "Enero" and s == 1:
                es_vacaciones = True; motivo = "REYES / AÑO NUEVO"
            elif mes == "Abril" and s == 1:
                es_vacaciones = True; motivo = "SEMANA SANTA"
            elif mes == "Junio" and s == semanas:
                es_vacaciones = True; motivo = "INICIO VERANO"
            elif mes == "Diciembre" and s == semanas:
                es_vacaciones = True; motivo = "NAVIDAD"

            if es_vacaciones:
                print(f"\n   🏖️  SEMANA {s} ({str_rango}): ⛔ CERRADO POR {motivo} ⛔")
                fecha_actual += timedelta(weeks=1)
                continue

            print(f"\n   ▶️  SEMANA {s} ({str_rango})")

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

                visitas, no_shows = motor.generar_flota_semanal(env, gym, socios_db, semana_absoluta, peso)

                if not visitas and not no_shows:
                    print("      ⚠️ Sin actividad registrada.")
                else:
                    env.process(motor.controlador_llegadas(env, visitas, admin_logs))
                    # --- CAMBIO AQUÍ: Pasamos 'visitas' al gestor ---
                    env.process(motor.gestor_semanal(env, admin_logs, fecha_actual, visitas))
                    env.run(until=cfg.TIEMPO_SEMANAL_SIMULACION)

                gym.cerrar_gimnasio()

                altas_para_reporte = altas_reales_este_mes if s == 1 else 0
                resumen = GeneradorReportes.generar_conclusiones_semanales(
                    visitas, no_shows, carpeta_sem, mes, s, semana_absoluta, socios_db, cfg, altas_para_reporte
                )
                historico_global.append(resumen)
                total_bajas += resumen["bajas"]

            except Exception as e:
                print(f"❌ Error crítico en semana {s}: {e}")
                raise e

            fecha_actual += timedelta(weeks=1)

    GeneradorReportes.generar_informe_anual(historico_global, raiz_logs)
    print(f"\n🎓 AÑO ACADÉMICO FINALIZADO. Bajas Totales: {total_bajas}")
    print(f"📁 Resultados completos en: {raiz_logs}")


if __name__ == "__main__":
    main()