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
    motor = MotorSimulacion(cfg, gestor_socios)
    socios_db = gestor_socios.inicializar_db()

    fecha_actual = datetime(2023, 9, 4)

    semana_absoluta = 0
    total_bajas = 0
    historico_global = []
    
    # Balance Económico
    total_acumulado = 0
    
    # Precios (cache)
    PRECIOS = cfg.datos["precios"]

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
        
        # --- CÁLCULO DE INGRESOS MENSUALES (SUSCRIPCIONES) ---
        ingresos_mes = 0, 0  # (Mensual, Pase Diario/Extra) -> Tuple doesn't support assignment. Let's use vars.
        ingresos_suscripciones = 0
        ingresos_pases = 0
        
        # Variables para acumular gastos de reparación de TODAS las semanas del mes
        gastos_reparaciones_mes = 0

        # 1. Cobrar a los socios existentes (Renovaciones anuales en Septiembre o Mensualidades)
        print(f"   💰 Procesando cobros para {len(socios_db)} socios...")
        for s in socios_db:
            if not s.get("activo", True): continue
            
            tipo = s.get("subtipo", "Estudiante")
            plan = s.get("plan_pago", "Mensual")
            
            # Obtener precio base
            coste = 0
            tarifas = PRECIOS.get(tipo, PRECIOS["Estudiante"])
            
            if plan == "Anual":
                # Si es Septiembre, cobranza anual general de renovacion
                # (Asumimos que todos renuevan en Septiembre para simplificar, o cuando entran)
                if mes == "Septiembre" and s["mes_alta"] != "Septiembre": # Si ya estaba de antes
                     coste = tarifas.get("Anual", 0) or tarifas.get("Mensual", 0) * 12 # Fallback
                elif s["mes_alta"] == mes: # Es nuevo de este mes (se cobrará más abajo o aquí si ya estaba en lista?
                     # Nota: si inyectamos despues, estos no estan aqui aun.
                     pass 
            else: # Mensual
                coste = tarifas.get("Mensual", 16)
            
            ingresos_suscripciones += coste

        altas_reales_este_mes = 0
        if altas_objetivo > 0:
            len_antes = len(socios_db)
            socios_db = gestor_socios.inyectar_nuevos(socios_db, altas_objetivo, mes)
            len_despues = len(socios_db)
            altas_reales_este_mes = len_despues - len_antes
            
            # Cobrar primera cuota a los NUEVOS
            nuevos = socios_db[len_antes:]
            for s in nuevos:
                tipo = s.get("subtipo", "Estudiante")
                plan = s.get("plan_pago", "Mensual")
                tarifas = PRECIOS.get(tipo, PRECIOS["Estudiante"])
                
                if plan == "Anual":
                    coste = tarifas.get("Anual", 0)
                else:
                    coste = tarifas.get("Mensual", 16)
                
                ingresos_suscripciones += coste
                
        print(f"      + Ingresos Suscripciones: {ingresos_suscripciones} €")

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
                motor.clasificar_maquinas(gym)
                # Pasar referencia de gimnasio a las máquinas (para reportar gastos)
                for m in gym.maquinas: 
                    m.gimnasio = gym
                    m.iniciar_simulacion(env)
                gym.abrir_gimnasio()

                visitas, no_shows = motor.generar_flota_semanal(env, gym, socios_db, semana_absoluta, peso)
                
                # --- INGRESOS POR PASES DIARIOS ---
                pases_diarios = sum(1 for u in visitas if u.tipo_usuario == "Pase_Diario")
                ingresos_pases += pases_diarios * PRECIOS["Pase_Diario"]

                if not visitas and not no_shows:
                    print("      ⚠️ Sin actividad registrada.")
                else:
                    env.process(motor.controlador_llegadas(env, visitas, admin_logs))
                    # --- CAMBIO AQUÍ: Pasamos 'visitas' al gestor ---
                    env.process(motor.gestor_semanal(env, admin_logs, fecha_actual, visitas))
                    env.run(until=cfg.TIEMPO_SEMANAL_SIMULACION)

                # Acumular gastos de reparación de esta semana
                gastos_reparaciones_mes += gym.costes_reparacion_acumulados
            
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


        
        # --- CÁLCULO FINAL DE BALANCE ---
        # 1. Salarios Monitores (1200 por monitor)
        # Asumimos que los monitores son constantes en número, cogemos del último 'gym' creado o 4 por defecto
        num_monitores = len(gym.monitores) if 'gym' in locals() and gym else 4 
        gastos_personal = num_monitores * cfg.datos["gastos"]["salario_monitor"]
        
        # 2. Reparaciones (Sumado semana a semana)
        
        gastos_totales = gastos_personal + gastos_reparaciones_mes
        balance_neto = (ingresos_suscripciones + ingresos_pases) - gastos_totales
        
        total_acumulado += balance_neto

        print(f"   💵 BALANCE {mes.upper()}:")
        print(f"      + Ingresos: {ingresos_suscripciones + ingresos_pases} €")
        print(f"      - Gastos Personal: {gastos_personal} €")
        print(f"      - Gastos Reparaciones: {gastos_reparaciones_mes} €")
        print(f"      = NETO: {balance_neto} € (Acumulado: {total_acumulado} €)")


    GeneradorReportes.generar_informe_anual(historico_global, raiz_logs)
    print(f"\n🎓 AÑO ACADÉMICO FINALIZADO.")
    print(f"   Bajas Totales: {total_bajas}")
    print(f"   GANANCIAS TOTALES: {total_acumulado} €")
    print(f"📁 Resultados completos en: {raiz_logs}")


if __name__ == "__main__":
    main()