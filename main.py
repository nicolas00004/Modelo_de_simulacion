import simpy
import os
from datetime import datetime, timedelta
from Config import Config
from Loggers import AdministradorDeLogs, GeneradorReportes
from GestorSocios import GestorSocios
from MotorSimulacion import MotorSimulacion
from Gimnasio import Gimnasio

def main():
    print("\n🚀 INICIANDO SIMULACIÓN ANUAL (V. FINAL)")
    print("=" * 60)

    cfg = Config()
    gestor_socios = GestorSocios(cfg)
    motor = MotorSimulacion(cfg, gestor_socios)
    socios_db = gestor_socios.inicializar_db()

    # El Gimnasio persiste todo el año para mantener el balance económico
    gym = Gimnasio()

    raiz_logs = f"Simulacion_{datetime.now().strftime('%H%M%S')}"
    os.makedirs(raiz_logs)
    print(f"📂 Carpeta de resultados: {raiz_logs}")

    fecha_actual = datetime(2023, 9, 4)
    total_bajas_año = 0
    historico_global = []

    for mes_cfg in cfg.CALENDARIO_ACADEMICO:
        mes = mes_cfg["mes"]
        if not mes_cfg["abierto"]: continue

        print(f"\n{'█' * 60}\n  📅 {mes.upper()}\n{'█' * 60}")
        carpeta_mes = f"{raiz_logs}/{mes}"
        os.makedirs(carpeta_mes, exist_ok=True)

        balance_inicio_mes = gym.balance

        # 1. COBROS MENSUALES
        socios_activos = [s for s in socios_db if s.get("activo", True)]
        ingresos_cuotas = 0
        for s in socios_activos:
            tarifa = cfg.datos["precios"].get(s["subtipo"], cfg.datos["precios"]["Estudiante"])
            cuota = tarifa["Anual"] if (s["plan_pago"] == "Anual" and mes == "Septiembre") else tarifa["Mensual"]
            ingresos_cuotas += cuota
        gym.balance += ingresos_cuotas

        # 2. ALTAS CONCENTRADAS (Picos de Enero/Septiembre)
        len_antes = len(socios_db)
        socios_db = gestor_socios.inyectar_nuevos(socios_db, mes_cfg["nuevas_altas_aprox"], mes)
        altas_mes = len(socios_db) - len_antes

        for s in socios_db[len_antes:]:
            tarifa = cfg.datos["precios"].get(s["subtipo"], cfg.datos["precios"]["Estudiante"])
            cuota = tarifa["Anual"] if s["plan_pago"] == "Anual" else tarifa["Mensual"]
            gym.balance += cuota
            ingresos_cuotas += cuota

        print(f"   💰 Ingresos Cuotas: {ingresos_cuotas}€ | Altas: +{altas_mes}")

        # 3. BUCLE SEMANAL
        for s in range(1, mes_cfg["semanas"] + 1):
            if (mes == "Enero" and s == 1) or (mes == "Diciembre" and s == 3):
                fecha_actual += timedelta(weeks=1)
                continue

            print(f"\n   ▶️ SEMANA {s} (Del {fecha_actual.strftime('%d/%m')} al {(fecha_actual + timedelta(days=6)).strftime('%d/%m')})")
            carpeta_sem = f"{carpeta_mes}/Semana_{s}"
            os.makedirs(carpeta_sem, exist_ok=True)

            env = simpy.Environment()
            admin_logs = AdministradorDeLogs(carpeta_sem)
            gym.costes_reparacion_acumulados = 0

            # Carga componentes vinculándolos al reloj de esta semana
            gym.cargar_datos_json(cfg.datos["rutas"]["archivo_gym"], env)

            motor.clasificar_maquinas(gym)
            for m in gym.maquinas:
                m.gimnasio = gym
                m.iniciar_simulacion(env)

            visitas, _ = motor.generar_flota_semanal(env, gym, socios_db, s, mes_cfg["peso_afluencia"])

            env.process(motor.controlador_llegadas(env, visitas, admin_logs))
            env.process(motor.gestor_semanal(env, admin_logs, fecha_actual, visitas))
            env.run(until=cfg.MINUTOS_MAXIMOS_POR_DIA * 6)

            # --- CORRECCIÓN: Ahora pasamos 'gym' como gym_obj ---
            resumen = GeneradorReportes.generar_conclusiones_semanales(
                visitas, [], carpeta_sem, mes, s, s, socios_db, cfg, altas_mes, gym
            )
            historico_global.append(resumen)
            total_bajas_año += resumen.get("bajas", 0)
            fecha_actual += timedelta(weeks=1)

        # 4. CIERRE DE MES (Gastos de Personal)
        gastos_nominas = len(gym.monitores) * cfg.datos["gastos"]["salario_monitor"]
        gym.balance -= gastos_nominas
        print(f"   📊 Resumen {mes}: Beneficio Neto {gym.balance - balance_inicio_mes:.2f}€")

    # 5. REPORTE ANUAL
    GeneradorReportes.generar_informe_anual(historico_global, raiz_logs)
    print(f"\n✅ SIMULACIÓN FINALIZADA. Bajas Totales: {total_bajas_año} | Capital Final: {gym.balance:.2f}€")

if __name__ == "__main__":
    main()