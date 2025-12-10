import json
import matplotlib.pyplot as plt
import os
import glob


def obtener_ultima_carpeta_logs(base_nombre="logs_anuales"):
    """Busca la carpeta logs_anuales con el número más alto."""
    carpetas = glob.glob(f"{base_nombre}*")
    if not carpetas:
        return None

    def extraer_numero(nombre):
        partes = nombre.split("_")
        if len(partes) > 2 and partes[2].isdigit():
            return int(partes[2])
        return 0

    carpetas_ordenadas = sorted(carpetas, key=extraer_numero, reverse=True)
    return carpetas_ordenadas[0]


def cargar_datos():
    carpeta = obtener_ultima_carpeta_logs()
    if not carpeta:
        print("❌ No se encontraron carpetas de logs.")
        return None

    archivo_json = os.path.join(carpeta, "Reporte_ANUAL_FINAL.json")

    if not os.path.exists(archivo_json):
        print(f"❌ No se encontró el reporte en {carpeta}")
        return None

    print(f"📂 Cargando datos de: {archivo_json}")
    with open(archivo_json, 'r', encoding='utf-8') as f:
        return json.load(f)


def generar_dashboard(datos):
    mensual = datos["mensual"]

    # Ejes X (Meses)
    meses = [m["mes"][:3] for m in mensual]

    # --- EXTRACCIÓN SEGURA DE DATOS (Evita errores si cambian los nombres) ---
    # Intenta buscar la clave nueva, si no existe, busca la vieja, si no, pone 0.

    visitas = [m.get("visitas", m.get("visitas_totales", 0)) for m in mensual]
    bajas = [m.get("bajas", m.get("bajas_totales", 0)) for m in mensual]

    # Aquí es donde te daba el error: buscamos 'sat_promedio', 'sat' o 'satisfaccion'
    satisfaccion = [m.get("sat_promedio", m.get("sat", m.get("satisfaccion", 0))) for m in mensual]

    # Buscamos 'socios_activos_fin_mes' o 'socios'
    socios = [m.get("socios_activos_fin_mes", m.get("socios", 0)) for m in mensual]

    # --- CONFIGURACIÓN GRÁFICA ---
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
    plt.subplots_adjust(hspace=0.4)

    # 1. Afluencia vs Bajas
    ax1.set_title("Afluencia vs. Deserción Mensual")
    ax1.bar(meses, visitas, color='#4a90e2', alpha=0.7, label='Visitas')
    ax1.set_ylabel("Total Visitas", color='#4a90e2', fontweight='bold')

    ax1_b = ax1.twinx()
    ax1_b.plot(meses, bajas, color='#e74c3c', marker='o', linewidth=2, label='Bajas')
    ax1_b.set_ylabel("Total Bajas", color='#e74c3c', fontweight='bold')

    for i, v in enumerate(bajas):
        ax1_b.text(i, v + 1, str(v), color='#e74c3c', fontweight='bold', ha='center')

    # 2. Satisfacción
    ax2.set_title("Calidad del Servicio (Satisfacción Media)")
    ax2.plot(meses, satisfaccion, color='#2ecc71', marker='s', linewidth=2)
    ax2.set_ylim(0, 100)
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='Aprobado')
    ax2.axhline(y=80, color='gold', linestyle='--', alpha=0.5, label='Excelencia')
    ax2.fill_between(meses, 0, 40, color='#e74c3c', alpha=0.1, label='Zona Crítica')
    ax2.set_ylabel("Puntos (0-100)")
    ax2.legend(loc="upper right")

    for i, v in enumerate(satisfaccion):
        ax2.text(i, v + 2, f"{v:.1f}", ha='center', fontsize=9)

    # 3. Socios Activos
    ax3.set_title("Evolución de la Cartera de Clientes")
    ax3.fill_between(meses, socios, color='#9b59b6', alpha=0.4)
    ax3.plot(meses, socios, color='#8e44ad', marker='o')
    ax3.set_ylabel("Socios Activos")

    for i, v in enumerate(socios):
        ax3.text(i, v, str(v), ha='center', va='bottom', fontweight='bold')

    print("📊 Generando gráficos...")
    plt.show()


if __name__ == "__main__":
    datos = cargar_datos()
    if datos:
        try:
            generar_dashboard(datos)
        except Exception as e:
            print(f"❌ Error generando gráficos: {e}")
            print("💡 Borra la carpeta logs_anuales y ejecuta main.py de nuevo para regenerar datos limpios.")