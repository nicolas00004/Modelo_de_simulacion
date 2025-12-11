import simpy
import random
from datetime import timedelta
from usuario import Usuario
from GestorSocios import PerfilGenerado


class MotorSimulacion:
    def __init__(self, config, gestor_socios=None):
        self.config = config
        self.gestor_socios = gestor_socios

    def clasificar_maquinas(self, gimnasio):
        pierna = ["Prensa", "Sentadilla", "Extensión", "Femoral", "Abductores", "Gemelos", "Hack"]
        torso = ["Press", "Jalón", "Remo", "Torre", "Dominadas", "Smith", "Scott", "Pecho"]
        for m in gimnasio.maquinas:
            if m.tipo_maquina == "Musculacion":
                if any(p in m.nombre for p in pierna):
                    m.tipo_maquina = "Musculacion_Pierna"
                elif any(p in m.nombre for p in torso):
                    m.tipo_maquina = "Musculacion_Torso"
                else:
                    m.tipo_maquina = "Musculacion_Torso"

    def generar_flota_semanal(self, env, gimnasio, base_datos, semana_abs, factor):
        programados = []
        lista_no_shows = []

        socios_permitidos = []
        for s in base_datos:
            if not s.get("activo", True): continue
            if s.get("castigado_hasta_semana_absoluta", 0) > semana_abs: continue
            socios_permitidos.append(s)

        cupo = int(self.config.CLIENTES_BASE * factor)
        print(f"   ℹ️ Acceso: {len(socios_permitidos)} permitidos | Cupo: ~{cupo} pax/sesión")

        if not socios_permitidos: return [], []

        for dia_idx, nombre_dia in enumerate(self.config.DIAS_SEMANA):
            sesiones = self.config.obtener_sesiones_por_dia(nombre_dia)
            reservados_hoy = set()

            for sesion in range(sesiones):
                var = self.config.datos["simulacion"]["variacion_afluencia"]
                reservas_totales = int(random.uniform(1.0 - var, 1.0 + var) * cupo)
                candidatos = [s for s in socios_permitidos if s['id'] not in reservados_hoy]
                if not candidatos: continue

                seleccionados = random.sample(candidatos, min(reservas_totales, len(candidatos)))
                inicio = (dia_idx * self.config.MINUTOS_MAXIMOS_POR_DIA) + (sesion * self.config.DURACION_SESION)

                for dato in seleccionados:
                    reservados_hoy.add(dato['id'])
                    es_no_show = random.random() < 0.05

                    if es_no_show:
                        lista_no_shows.append(dato['id'])
                    else:
                        u = Usuario(
                            id_usuario=dato["id"], nombre=dato["nombre"], tipo_usuario="Socio",
                            subtipo=dato.get("subtipo", "Estudiante"), plan_pago=dato.get("plan_pago", "Mensual"),
                            tiempo_llegada=inicio + random.uniform(0, 10), hora_fin=inicio + random.randint(60, 90),
                            rutina=dato["rutina"], perfil=PerfilGenerado(dato["perfil"]), problema=None,
                            config=self.config.datos, env=env, gimnasio=gimnasio,
                            faltas_consecutivas=dato["faltas_consecutivas"]
                        )
                        u.satisfaccion = dato.get("satisfaccion_acumulada", 100)
                        programados.append(u)

                # --- GENERACIÓN DE PASES DIARIOS ---
                prob_pase = self.config.datos.get("probabilidades", {}).get("pase_diario", 0.05)
                # Intentamos generar algunos pases diarios extra (independientes del cupo de socios)
                n_pases = int(random.uniform(0, 2)) if random.random() < prob_pase else 0
                
                for _ in range(n_pases):
                    # Crear usuario ficticio de pase diario
                    inicio_pase = (dia_idx * self.config.MINUTOS_MAXIMOS_POR_DIA) + (sesion * self.config.DURACION_SESION)
                    
                    # Generar perfil aleatorio
                    perfil_dummy = {"tipo": "Mix", "energia": 200, "prob_descanso": 0.3}
                    rutina_dummy = [{"tipo_maquina_deseada": "Cardio", "tiempo_uso": 20}, {"tipo_maquina_deseada": "Musculacion_Torso", "tiempo_uso": 30}]
                    
                    u_pase = Usuario(
                        id_usuario=999999 + random.randint(1, 9999), nombre=f"Visitante-{random.randint(100,999)}", 
                        tipo_usuario="Pase_Diario", subtipo="Visitante", plan_pago="Diario",
                        tiempo_llegada=inicio_pase + random.uniform(5, 15), hora_fin=inicio_pase + 90,
                        rutina=rutina_dummy, perfil=PerfilGenerado(perfil_dummy), problema=None,
                        config=self.config.datos, env=env, gimnasio=gimnasio
                    )
                    programados.append(u_pase)

        return programados, lista_no_shows

    def controlador_llegadas(self, env, usuarios, admin_logs):
        usuarios.sort(key=lambda u: u.tiempo_llegada)
        for u in usuarios:
            yield env.timeout(u.tiempo_llegada - env.now)
            dia_idx = int(env.now // self.config.MINUTOS_MAXIMOS_POR_DIA)
            if dia_idx >= len(self.config.DIAS_SEMANA): break

            u.logger_sesion = admin_logs
            u.dia_sesion = self.config.DIAS_SEMANA[dia_idx]
            u.numero_sesion = int((env.now % self.config.MINUTOS_MAXIMOS_POR_DIA) // self.config.DURACION_SESION) + 1

            admin_logs.log(f"➕ {u.nombre} entra", "LLEGADA")
            admin_logs.registrar_datos(
                {"tiempo_simulacion": f"{env.now:.2f}", "tipo_evento": "LLEGADA", "id_usuario": u.id,
                 "nombre": u.nombre, "dia": u.dia_sesion, "sesion": u.numero_sesion,
                 "satisfaccion_actual": u.satisfaccion})
            admin_logs.registrar_entrada_usuario()

            # Wrapper para controlar el fin de sesión y conversiones
            u.process = env.process(self._wrapper_entrenamiento(env, u, admin_logs))

    def _wrapper_entrenamiento(self, env, usuario, admin_logs):
        """Envuelve el proceso de entrenamiento para ejecutar lógica post-sesión."""
        try:
            yield from usuario.entrenar(90)
        except simpy.Interrupt as i:
            # Si fue interrumpido (ej. fin de sesión), propagamos o manejamos
            # Pero usuario.entrenar ya maneja interrupciones internas.
            pass
        
        # --- Lógica de Conversión ---
        if usuario.tipo_usuario == "Pase_Diario" and self.gestor_socios:
            sat = usuario.satisfaccion
            umbrales = self.config.datos["probabilidades"]["conversion"]
            nuevo_plan = None
            
            if sat >= umbrales["umbral_anual"]:
                nuevo_plan = "Anual"
            elif sat >= umbrales["umbral_mensual"]:
                nuevo_plan = "Mensual"
            
            if nuevo_plan:
                # CONVERTIR
                print(f"      ✨ ¡NUEVA CONVERSIÓN! {usuario.nombre} (Sat: {sat}) -> Plan {nuevo_plan}")
                admin_logs.log(f"Convierte a {nuevo_plan}", "CONVERSION")
                self.gestor_socios.convertir_pase_diario(usuario, nuevo_plan, usuario.dia_sesion) # Pasamos día como fecha aprox
            else:
                print(f"      👋 {usuario.nombre} no se inscribe (Sat: {sat})")

    # --- MODIFICADO: AHORA RECIBE 'usuarios_programados' PARA EXPULSARLOS ---
    def gestor_semanal(self, env, admin_logs, fecha_lunes, usuarios_programados):
        for i, dia in enumerate(self.config.DIAS_SEMANA):
            fecha_dia = fecha_lunes + timedelta(days=i)
            fecha_str = fecha_dia.strftime("%d/%m/%Y")

            print(f"\n      🌞 {dia.upper()} [{fecha_str}]")
            print(f"      {'-' * 30}")

            sesiones = self.config.obtener_sesiones_por_dia(dia)
            for s in range(1, sesiones + 1):
                admin_logs.cambiar_sesion(dia, s)

                hora_inicio = env.now
                print(f"         🔔 [T={hora_inicio:.0f}] Inicio Sesión {s}")

                yield env.timeout(self.config.DURACION_SESION)

                hora_fin = env.now
                print(f"         🔕 [T={hora_fin:.0f}] Fin Sesión {s}")

                # --- LÓGICA DE EXPULSIÓN ---
                # Buscamos a cualquiera cuyo proceso siga vivo
                expulsados = 0
                for u in usuarios_programados:
                    if u.process and u.process.is_alive:
                        # Comprobamos que sea del día actual (para no interrumpir a gente de mañana)
                        # Aunque 'process.is_alive' solo será true si ya ha llegado
                        try:
                            u.process.interrupt(cause="FIN_SESION")
                            expulsados += 1
                        except RuntimeError:
                            # Puede pasar si el proceso muere justo en este milisegundo
                            pass

                if expulsados > 0:
                    print(f"         🚨 Se expulsó a {expulsados} usuarios al cerrar la sesión.")

            restante = (self.config.MINUTOS_MAXIMOS_POR_DIA - sesiones * self.config.DURACION_SESION)
            if restante > 0: yield env.timeout(restante)