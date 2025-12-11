import json
import matplotlib.pyplot as plt
import os
import glob
import numpy as np


# --- FUNCIONES DE CARGA ---

def obtener_ultima_carpeta_logs(base_nombre="logs_anuales"):
    carpetas = glob.glob(f"{base_nombre}*")
    if not carpetas: return None

    def extraer_numero(nombre):
        partes = nombre.split("_")
        if len(partes) > 2 and partes[2].isdigit(): return int(partes[2])
        return 0

    carpetas_ordenadas = sorted(carpetas, key=extraer_numero, reverse=True)
    return carpetas_ordenadas[0]


def cargar_datos_anuales():
    """Carga el resumen temporal (Reporte_ANUAL_FINAL.json)"""
    carpeta = obtener_ultima_carpeta_logs()
    if not carpeta: return None

    archivo = os.path.join(carpeta, "Reporte_ANUAL_FINAL.json")
    if not os.path.exists(archivo): return None

    print(f"📂 Cargando Reporte Anual: {archivo}")
    with open(archivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def cargar_datos_clientes():
    """Carga la base de datos de clientes (datos_clientes.json)"""
    # Buscamos en la raíz primero
    archivo = "datos_clientes.json"
    if not os.path.exists(archivo):
        # Si no está en raíz, miramos en la carpeta de logs
        carpeta = obtener_ultima_carpeta_logs()
        if carpeta:
            archivo = os.path.join(carpeta, "datos_clientes.json")

    if not os.path.exists(archivo):
        print("❌ No se encontró 'datos_clientes.json'.")
        return None

    print(f"👥 Cargando Base de Socios: {archivo}")
    with open(archivo, 'r', encoding='utf-8') as f:
        return json.load(f)


# --- VENTANA 1: EVOLUCIÓN TEMPORAL ---

def generar_dashboard_evolucion(datos):
    mensual = datos["mensual"]
    meses = [m["mes"][:3] for m in mensual]

    visitas = [m.get("visitas", m.get("visitas_totales", 0)) for m in mensual]
    bajas = [m.get("bajas", m.get("bajas_totales", 0)) for m in mensual]
    satisfaccion = [m.get("sat_promedio", m.get("sat", 0)) for m in mensual]
    socios = [m.get("socios_activos_fin_mes", m.get("socios", 0)) for m in mensual]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
    fig.canvas.manager.set_window_title('Dashboard 1: Evolución Temporal')
    plt.subplots_adjust(hspace=0.4)

    # 1. Afluencia
    ax1.set_title("Afluencia vs. Deserción Mensual")
    ax1.bar(meses, visitas, color='#4a90e2', alpha=0.7, label='Visitas')
    ax1.set_ylabel("Visitas", color='#4a90e2', fontweight='bold')
    ax1_b = ax1.twinx()
    ax1_b.plot(meses, bajas, color='#e74c3c', marker='o', linewidth=2, label='Bajas')
    ax1_b.set_ylabel("Bajas", color='#e74c3c', fontweight='bold')
    for i, v in enumerate(bajas): ax1_b.text(i, v + 1, str(v), color='#e74c3c', ha='center', fontsize=8)

    # 2. Satisfacción
    ax2.set_title("Calidad del Servicio (Satisfacción Media)")
    ax2.plot(meses, satisfaccion, color='#2ecc71', marker='s', linewidth=2)
    ax2.set_ylim(0, 100)
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax2.fill_between(meses, 0, 40, color='#e74c3c', alpha=0.1)
    ax2.set_ylabel("Puntos")
    for i, v in enumerate(satisfaccion): ax2.text(i, v + 3, f"{v:.1f}", ha='center', fontsize=8)

    # 3. Socios Activos
    ax3.set_title("Evolución de la Cartera de Clientes")
    ax3.fill_between(meses, socios, color='#9b59b6', alpha=0.4)
    ax3.plot(meses, socios, color='#8e44ad', marker='o')
    ax3.set_ylabel("Socios Activos")
    for i, v in enumerate(socios): ax3.text(i, v, str(v), ha='center', va='bottom', fontsize=8)


# --- VENTANA 2: ANÁLISIS DEMOGRÁFICO ---

def generar_dashboard_demografico(clientes):
    # Procesar datos
    generos = {"Masculino": {"total": 0, "bajas": 0, "sat": []},
               "Femenino": {"total": 0, "bajas": 0, "sat": []}}

    perfiles = {}  # Dinámico (Fuerza, Mixto...)

    for c in clientes:
        # Género
        g = c["genero"]
        generos[g]["total"] += 1
        generos[g]["sat"].append(c["satisfaccion_acumulada"])
        if not c["activo"]: generos[g]["bajas"] += 1

        # Perfil
        p = c["perfil"]["tipo"]
        if p not in perfiles: perfiles[p] = {"total": 0, "bajas": 0, "sat": []}
        perfiles[p]["total"] += 1
        perfiles[p]["sat"].append(c["satisfaccion_acumulada"])
        if not c["activo"]: perfiles[p]["bajas"] += 1

    # Crear Gráficos
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.canvas.manager.set_window_title('Dashboard 2: Análisis de Clientes (Género y Perfil)')
    plt.subplots_adjust(hspace=0.4, wspace=0.3)

    # 1. Distribución por Género (Pie Chart)
    ax1 = axes[0, 0]
    sizes_g = [generos["Masculino"]["total"], generos["Femenino"]["total"]]
    labels_g = [f"Hombres ({sizes_g[0]})", f"Mujeres ({sizes_g[1]})"]
    colors_g = ['#3498db', '#e91e63']
    ax1.pie(sizes_g, labels=labels_g, colors=colors_g, autopct='%1.1f%%', startangle=90)
    ax1.set_title("Distribución por Género")

    # 2. Tasa de Abandono por Género (Barras)
    ax2 = axes[0, 1]
    tasa_bajas_h = (generos["Masculino"]["bajas"] / generos["Masculino"]["total"] * 100) if generos["Masculino"][
        "total"] else 0
    tasa_bajas_m = (generos["Femenino"]["bajas"] / generos["Femenino"]["total"] * 100) if generos["Femenino"][
        "total"] else 0

    barras = ax2.bar(["Hombres", "Mujeres"], [tasa_bajas_h, tasa_bajas_m], color=['#3498db', '#e91e63'])
    ax2.set_title("% de Bajas según Género")
    ax2.set_ylabel("% de Abandono")
    ax2.set_ylim(0, max(tasa_bajas_h, tasa_bajas_m) + 10)

    for bar in barras:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2., height, f'{height:.1f}%', ha='center', va='bottom')

    # 3. Distribución por Perfil (Pie Chart)
    ax3 = axes[1, 0]
    labels_p = list(perfiles.keys())
    sizes_p = [perfiles[k]["total"] for k in labels_p]
    # Generar colores dinámicos
    colors_p = plt.cm.Paired(np.linspace(0, 1, len(labels_p)))

    ax3.pie(sizes_p, labels=labels_p, colors=colors_p, autopct='%1.1f%%', startangle=140)
    ax3.set_title("Tipos de Perfil de Usuario")

    # 4. Satisfacción Media por Perfil (Barras Horizontales)
    ax4 = axes[1, 1]
    sat_p = [sum(perfiles[k]["sat"]) / len(perfiles[k]["sat"]) if perfiles[k]["sat"] else 0 for k in labels_p]

    y_pos = np.arange(len(labels_p))
    ax4.barh(y_pos, sat_p, color='#f1c40f')
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(labels_p)
    ax4.set_xlabel("Puntos (0-100)")
    ax4.set_title("Satisfacción Media por Perfil")
    ax4.set_xlim(0, 100)

    for i, v in enumerate(sat_p):
        ax4.text(v + 1, i, f"{v:.1f}", va='center', fontweight='bold')

    print("📊 Generando gráficos demográficos...")


# --- MAIN ---

if __name__ == "__main__":
    datos_anuales = cargar_datos_anuales()
    datos_clientes = cargar_datos_clientes()

    if datos_anuales:
        generar_dashboard_evolucion(datos_anuales)

    if datos_clientes:
        generar_dashboard_demografico(datos_clientes)

    if datos_anuales or datos_clientes:
        print("✅ Gráficos generados. Revisa las ventanas emergentes.")
        plt.show()  # Muestra todas las ventanas a la vez
    else:
        print("⚠️ No se pudieron cargar datos. Asegúrate de haber ejecutado 'main.py' primero.")