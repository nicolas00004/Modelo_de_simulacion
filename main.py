import simpy
from Gimnasio import Gimnasio
from usuario import Usuario  # Nota: asegúrate de que sea 'Usuario' o 'usuario' según tu nombre de archivo real
from Logs import Logs  # Importamos tu nueva clase


def controlador_de_llegadas(env, lista_usuarios, logger):
    """
    Controla la entrada de usuarios y registra los eventos en el Log y CSV.
    """
    # Ordenamos por tiempo de llegada
    lista_usuarios.sort(key=lambda u: u.tiempo_llegada)

    for usuario in lista_usuarios:
        # Esperar hasta la llegada del usuario
        tiempo_a_esperar = usuario.tiempo_llegada - env.now
        if tiempo_a_esperar > 0:
            yield env.timeout(tiempo_a_esperar)

        # --- LOG DE EVENTO (Texto) ---
        mensaje = f"🚪 PUERTA: Entra {usuario.nombre} (ID: {usuario.id})"
        logger.log(mensaje, "LLEGADA")
        print(f"[{env.now:6.2f}] {mensaje}")  # Mantenemos print para verlo en consola también

        # --- LOG DE ESTADÍSTICA (CSV) ---
        # Registramos que ha llegado un usuario. Esto creará una fila en el Excel.
        datos_usuario = {
            "tiempo_simulacion": f"{env.now:.2f}",
            "tipo_evento": "LLEGADA_CLIENTE",
            "id_usuario": usuario.id,
            "nombre": usuario.nombre,
            "tipo_suscripcion": usuario.tipo_usuario,
            "perfil_energia": usuario.perfil.energia if usuario.perfil else 0
        }
        logger.registrar_datos(datos_usuario)

        # Calcular duración
        duracion = usuario.hora_fin - usuario.tiempo_llegada
        if duracion <= 0:
            duracion = 60

        # Iniciar entrenamiento
        # NOTA: Si quisieras logs dentro de 'entrenar', tendrías que pasar 'logger' aquí también
        # env.process(usuario.entrenar(tiempo_total=duracion, logger=logger))
        env.process(usuario.entrenar(tiempo_total=duracion))


def main():
    # 1. INICIALIZAR LOGGER
    # Esto creará la carpeta /logs y los archivos .log y .csv
    logger = Logs("simulacion_gimnasio_v1")

    logger.log("========================================", "INIT")
    logger.log("   INICIANDO SIMULACIÓN DEL GIMNASIO    ", "INIT")
    logger.log("========================================", "INIT")

    env = simpy.Environment()
    TIEMPO_SIMULACION = 200

    # Guardamos los parámetros iniciales en el log
    logger.log_parametros(
        archivo_gym="datos_gimnasio.json",
        archivo_clientes="datos_clientes.json",
        tiempo_simulacion=TIEMPO_SIMULACION
    )

    try:
        # 2. CARGAR GIMNASIO
        logger.log("Cargando Infraestructura...", "SETUP")
        mi_gimnasio = Gimnasio()
        mi_gimnasio.cargar_datos_json("datos_gimnasio.json")

        logger.log(f"Infraestructura cargada: {len(mi_gimnasio.maquinas)} máquinas.", "SETUP")

        logger.log("Activando máquinas en SimPy...", "SETUP")
        for maquina in mi_gimnasio.maquinas:
            maquina.iniciar_simulacion(env)

        mi_gimnasio.abrir_gimnasio()

        # 3. CARGAR CLIENTES
        logger.log("Cargando Clientes...", "SETUP")
        lista_usuarios = Usuario.generar_desde_json("datos_clientes.json", env, mi_gimnasio)

        if not lista_usuarios:
            logger.log("No hay usuarios cargados. Abortando.", "ERROR")
            return

        logger.log(f"Se cargaron {len(lista_usuarios)} clientes.", "SETUP")

        # 4. CORRER SIMULACIÓN
        # Pasamos el 'logger' al controlador
        env.process(controlador_de_llegadas(env, lista_usuarios, logger))

        logger.log("--- ⏯️  PLAY SIMULACIÓN ---", "RUN")
        env.run(until=TIEMPO_SIMULACION)

        logger.log("========================================", "FIN")
        mi_gimnasio.cerrar_gimnasio()

    except Exception as e:
        # Capturamos cualquier error inesperado y lo guardamos en el log
        logger.log(f"Ocurrió un error crítico: {e}", "FATAL")
        raise e  # Relanzamos el error para verlo en consola también


if __name__ == "__main__":
    main()