import random
from datetime import datetime, timedelta, time
from usuario import Usuario
from GestorSocios import PerfilGenerado


class MotorSimulacion:
    def __init__(self, config, gestor_socios=None):
        self.config = config
        self.gestor_socios = gestor_socios

    def clasificar_maquinas(self, gimnasio):
        """Clasifica máquinas de musculación en categorías específicas para las rutinas."""
        pierna = ["Prensa", "Sentadilla", "Extensión", "Femoral", "Abductores", "Gemelos", "Hack"]
        torso = ["Press", "Jalón", "Remo", "Torre", "Dominadas", "Smith", "Scott", "Pecho"]
        for m in gimnasio.maquinas:
            if m.tipo_maquina == "Musculacion":
                if any(p in m.nombre for p in pierna):
                    m.tipo_maquina = "Musculacion_Pierna"
                else:
                    m.tipo_maquina = "Musculacion_Torso"

    def generar_flota_semanal(self, env, gimnasio, base_datos, semana_abs, factor):
        """Genera la lista de usuarios que asistirán esta semana, filtrando bajas."""
        programados = []
        # Solo socios que sigan activos en la base de datos
        socios_permitidos = [s for s in base_datos if s.get("activo", True)]
        cupo = int(self.config.CLIENTES_BASE * factor)

        for dia_idx, nombre_dia in enumerate(self.config.DIAS_SEMANA):
            sesiones = self.config.obtener_sesiones_por_dia(nombre_dia)
            reservados_hoy = set()

            for sesion in range(sesiones):
                var = self.config.datos["simulacion"]["variacion_afluencia"]
                reservas_totales = int(random.uniform(1.0 - var, 1.0 + var) * cupo)
                candidatos = [s for s in socios_permitidos if s['id'] not in reservados_hoy]

                if candidatos:
                    seleccionados = random.sample(candidatos, min(reservas_totales, len(candidatos)))
                    inicio = (dia_idx * self.config.MINUTOS_MAXIMOS_POR_DIA) + (sesion * self.config.DURACION_SESION)

                    for dato in seleccionados:
                        reservados_hoy.add(dato['id'])
                        if random.random() > 0.05:  # Probabilidad de No-Show (5%)
                            u = Usuario(
                                env=env, gimnasio=gimnasio, id_usuario=dato["id"], nombre=dato["nombre"],
                                tipo_usuario="Socio", subtipo=dato.get("subtipo", "Estudiante"),
                                plan_pago=dato.get("plan_pago", "Mensual"),
                                tiempo_llegada=inicio + random.uniform(0, 10), hora_fin=inicio + 90,
                                rutina=dato["rutina"], perfil=PerfilGenerado(dato["perfil"]),
                                problema=None, config=self.config.datos, faltas_consecutivas=dato["faltas_consecutivas"]
                            )
                            u.satisfaccion = dato.get("satisfaccion_acumulada", 100)
                            programados.append(u)

                # --- GENERACIÓN DE PASES DIARIOS ---
                if random.random() < 0.15:
                    precio_pase = self.config.datos["precios"].get("Pase_Diario", 10)
                    gimnasio.balance += precio_pase

                    # Garantizar ID único para el día
                    while True:
                        new_id = random.randint(9000, 9999)
                        if new_id not in reservados_hoy:
                            reservados_hoy.add(new_id)
                            break
                    
                    u_pase = Usuario(
                        env=env, gimnasio=gimnasio, id_usuario=new_id,
                        nombre=f"Visitante-{random.randint(100, 999)}", tipo_usuario="Pase_Diario",
                        subtipo="Visitante", plan_pago="Diario",
                        tiempo_llegada=inicio + random.uniform(10, 30), hora_fin=inicio + 90,
                        rutina=[{"tipo_maquina_deseada": "Cardio", "tiempo_uso": 30}],
                        perfil=PerfilGenerado({"tipo": "Mix", "energia": 100, "prob_descanso": 0.2}),
                        problema=None, config=self.config.datos
                    )
                    programados.append(u_pase)

        return programados, []

    def _wrapper_entrenamiento(self, env, u, admin_logs):
        """Ejecuta el entrenamiento y gestiona la posible conversión de visitantes a socios."""
        try:
            yield from u.entrenar(90)
            if u.tipo_usuario == "Pase_Diario" and u.satisfaccion > 70:
                # Decidir plan (60% Mensual, 40% Anual - similar a generación inicial)
                plan_elegido = "Mensual" if random.random() < 0.6 else "Anual"
                
                # Calcular pago inicial según el plan
                # Asumimos tarifa de Estudiante para nuevos conversos por ahora
                tarifa = self.config.datos["precios"]["Estudiante"]
                pago = tarifa[plan_elegido]
                
                u.gimnasio.balance += pago
                msg = f"      ✨ ¡CONVERSIÓN! {u.nombre} se apunta al centro ({plan_elegido}: +{pago}€)"
                print(msg)
                admin_logs.log(msg)
                
                if self.gestor_socios:
                    self.gestor_socios.convertir_pase_diario(u, plan_elegido, u.dia_sesion)
        except:
            pass

    def gestor_semanal(self, env, admin_logs, fecha_lunes, usuarios_programados):
        """Maneja el calendario semanal, abre/cierra sesiones y gestiona la consola/logs."""
        HORA_APERTURA = 8

        for i, dia in enumerate(self.config.DIAS_SEMANA):
            fecha_dia = fecha_lunes + timedelta(days=i)
            fecha_str = fecha_dia.strftime("%d/%m/%Y")

            # Registro visual del nuevo día
            msg_dia = f"\n{'=' * 65}\n 🌞 {dia.upper()} [{fecha_str}]\n{'=' * 65}"
            print(msg_dia)

            sesiones = self.config.obtener_sesiones_por_dia(dia)
            for s in range(1, sesiones + 1):
                minutos_sesion = (s - 1) * self.config.DURACION_SESION
                momento_inicio = datetime.combine(fecha_dia, time(HORA_APERTURA, 0)) + \
                                 timedelta(minutes=minutos_sesion)

                # --- INICIO DE SESIÓN ---
                admin_logs.cambiar_sesion(dia, s)
                msg_inicio = f"   🔔 [{momento_inicio.strftime('%H:%M')}] >>> INICIO Sesión {s}"
                print(msg_inicio)
                admin_logs.log(msg_inicio)

                yield env.timeout(self.config.DURACION_SESION)

                # --- FIN DE SESIÓN ---
                momento_fin = momento_inicio + timedelta(minutes=self.config.DURACION_SESION)
                msg_fin = f"   🔕 [{momento_fin.strftime('%H:%M')}] <<< FIN Sesión {s}"
                print(msg_fin)
                admin_logs.log(msg_fin)

                # Expulsión de usuarios rezagados
                expulsados = 0
                for u in usuarios_programados:
                    if u.process and u.process.is_alive:
                        try:
                            u.process.interrupt(cause="FIN_SESION")
                            expulsados += 1
                        except:
                            pass

                if expulsados > 0:
                    msg_exp = f"      🚨 {expulsados} usuarios desalojados por fin de turno."
                    print(msg_exp)
                    admin_logs.log(msg_exp)

                admin_logs.finalizar_sesion()

            # Descanso nocturno
            restante = self.config.MINUTOS_MAXIMOS_POR_DIA - (sesiones * self.config.DURACION_SESION)
            if restante > 0: yield env.timeout(restante)

    def controlador_llegadas(self, env, usuarios, admin_logs):
        """Gestiona la entrada de usuarios al gimnasio cronológicamente."""
        usuarios.sort(key=lambda u: u.tiempo_llegada)
        for u in usuarios:
            yield env.timeout(max(0, u.tiempo_llegada - env.now))

            # Metadata de sesión para el usuario
            u.logger_sesion = admin_logs
            dia_idx = int(env.now // self.config.MINUTOS_MAXIMOS_POR_DIA)
            u.dia_sesion = self.config.DIAS_SEMANA[min(dia_idx, 5)]

            minutos_hoy = env.now % self.config.MINUTOS_MAXIMOS_POR_DIA
            u.numero_sesion = int(minutos_hoy // self.config.DURACION_SESION) + 1

            # --- REGISTRO DE LLEGADA (CONSOLA Y TXT) ---
            msg_llegada = f"   [T={env.now:7.2f}] 🚪 {u.nombre.ljust(25)} (ID: {u.id}) ha llegado a la recepción."
            print(msg_llegada)
            admin_logs.log(msg_llegada)

            admin_logs.registrar_entrada_usuario()
            u.process = env.process(self._wrapper_entrenamiento(env, u, admin_logs))