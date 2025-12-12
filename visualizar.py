import json
import matplotlib.pyplot as plt
import os
import glob
import warnings
from collections import Counter

# Silenciar avisos de fuentes para evitar el molesto mensaje del Glyph
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")


def obtener_ultima_carpeta_logs(base_nombre="Simulacion"):
    """Localiza la carpeta de resultados más reciente."""
    carpetas = glob.glob(f"{base_nombre}*") + glob.glob("logs_anuales*")
    if not carpetas: return None
    return max(carpetas, key=os.path.getmtime)


def cargar_json(ruta):
    if not os.path.exists(ruta): return None
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)


def generar_dashboard_maestro():
    # 1. CARGA DE ARCHIVOS
    carpeta = obtener_ultima_carpeta_logs()
    if not carpeta:
        print("Error: No se detectan carpetas de simulacion.")
        return

    reporte_anual = cargar_json(os.path.join(carpeta, "Reporte_ANUAL_FINAL.json"))
    db_clientes = cargar_json("datos_clientes.json")

    if not reporte_anual or not db_clientes:
        print("Error: Faltan archivos criticos para el analisis (JSON).")
        return

    # 2. PROCESAMIENTO DE DATOS (Simulacion)
    mensual = reporte_anual.get("historico_detallado", reporte_anual.get("detalle_mensual", []))
    meses = [m.get("mes", "S/N")[:3] for m in mensual]

    asistentes = [m.get("asistentes", 0) for m in mensual]
    bajas = [m.get("bajas", 0) for m in mensual]
    satisfaccion = [m.get("satisfaccion", 0) for m in mensual]
    # Extraemos los ACUMULADOS del log (Balance y Costes Totales)
    balance_acumulado = [m.get("ingresos_mes", 0) for m in mensual]
    gastos_acumulado = [m.get("gastos_mes", 0) for m in mensual]

    # Calculamos los flujos MENSUALES (Deltas)
    ingresos = []
    gastos = []
    beneficio = []

    ultimo_balance = 25000  # Capital Inicial (Hardcoded en Gimnasio.py)
    ultimo_gasto = 0

    for bal, gas_acum in zip(balance_acumulado, gastos_acumulado):
        # Gastos del periodo = Gasto Acumulado Actual - Gasto Acumulado Anterior
        gasto_mes = gas_acum - ultimo_gasto

        # Ingresos del periodo = (Balance Actual - Balance Anterior) + Gastos del periodo
        # Derivado de: Balance_Actual = Balance_Anterior + Ingresos - Gastos
        ingreso_mes = (bal - ultimo_balance) + gasto_mes

        # Beneficio Neto = Ingresos - Gastos
        ben_mes = ingreso_mes - gasto_mes

        ingresos.append(ingreso_mes)
        gastos.append(gasto_mes)
        beneficio.append(ben_mes)

        ultimo_balance = bal
        ultimo_gasto = gas_acum
    activos_evolucion = [m.get("socios_activos", 0) for m in mensual]

    # 3. PROCESAMIENTO DE CLIENTES (Demografia y Rutinas)
    tipos_socio = Counter([c["subtipo"] for c in db_clientes])
    planes = Counter([c["plan_pago"] for c in db_clientes])

    demandas_maq = []
    for c in db_clientes:
        for paso in c.get("rutina", []):
            demandas_maq.append(paso["tipo_maquina_deseada"])
    top_maquinas = Counter(demandas_maq)

    # --- CONFIGURACION VISUAL (Grid 4x2) ---
    # Hemos eliminado los emojis de los titulos para evitar el error de Glyph
    fig = plt.figure(figsize=(18, 16))
    plt.subplots_adjust(hspace=0.6, wspace=0.3)
    fig.suptitle(f"PANEL DE CONTROL INTEGRAL: {carpeta}", fontsize=20, fontweight='bold')

    # GRAFICO 1: Operaciones (Asistencia vs Bajas)
    ax1 = plt.subplot(4, 2, 1)
    ax1.bar(meses, asistentes, color='#3498db', alpha=0.5, label='Asistentes')
    ax1_b = ax1.twinx()
    ax1_b.plot(meses, bajas, color='#e74c3c', marker='o', label='Bajas')
    ax1.set_title("Afluencia vs. Desercion", fontweight='bold')
    ax1.legend(loc='upper left')

    # GRAFICO 2: Calidad (Satisfaccion)
    ax2 = plt.subplot(4, 2, 2)
    ax2.plot(meses, satisfaccion, color='#f1c40f', marker='s', linewidth=2)
    ax2.fill_between(meses, satisfaccion, color='#f1c40f', alpha=0.1)
    ax2.axhline(25, color='red', linestyle='--', alpha=0.3)
    ax2.set_title("Satisfaccion Media (0-100)", fontweight='bold')
    ax2.set_ylim(0, 105)

    # GRAFICO 3: Economia (Ingresos vs Gastos)
    ax3 = plt.subplot(4, 2, 3)
    x = range(len(meses))
    ax3.bar(x, ingresos, width=0.4, label='Ingresos', color='#2ecc71', align='center')
    ax3.bar(x, gastos, width=0.4, label='Gastos', color='#e67e22', align='edge')
    ax3.set_xticks(x)
    ax3.set_xticklabels(meses)
    ax3.set_title("Balance Economico (Euro)", fontweight='bold')
    ax3.legend()

    # GRAFICO 4: Rentabilidad (Beneficio Neto)
    ax4 = plt.subplot(4, 2, 4)
    colores_ben = ['#2ecc71' if b > 0 else '#e74c3c' for b in beneficio]
    ax4.bar(meses, beneficio, color=colores_ben)
    ax4.axhline(0, color='black', linewidth=1)
    ax4.set_title("Beneficio Neto Mensual", fontweight='bold')

    # GRAFICO 5: Clientes (Segmentacion)
    ax5 = plt.subplot(4, 2, 5)
    ax5.pie(tipos_socio.values(), labels=tipos_socio.keys(), autopct='%1.1f%%', startangle=140)
    ax5.set_title("Segmentacion por Perfil", fontweight='bold')

    # GRAFICO 6: Fidelizacion (Planes)
    ax6 = plt.subplot(4, 2, 6)
    ax6.pie(planes.values(), labels=planes.keys(), autopct='%1.1f%%', colors=['#1abc9c', '#34495e'])
    ax6.set_title("Mix de Planes (Anual vs Mensual)", fontweight='bold')

    # GRAFICO 7: Cartera Activa (Evolucion Socios)
    ax7 = plt.subplot(4, 2, 7)
    ax7.plot(meses, activos_evolucion, color='#8e44ad', marker='D', linestyle=':')
    ax7.set_title("Total Socios Activos", fontweight='bold')

    # GRAFICO 8: Demanda (Maquinas mas pedidas)
    ax8 = plt.subplot(4, 2, 8)
    ax8.barh(list(top_maquinas.keys()), list(top_maquinas.values()), color='#1abc9c')
    ax8.set_title("Demanda por Tipo de Maquina", fontweight='bold')

    print("Dashboard generado correctamente.")
    plt.show()


if __name__ == "__main__":
    generar_dashboard_maestro()