import simpy
import random
from usuario import Usuario
from GestorSocios import PerfilGenerado


class MotorSimulacion:
    def __init__(self, config):
        self.config = config

    def clasificar_maquinas(self, gimnasio):
        pierna = ["Prensa", "Sentadilla", "Extensión", "Femoral", "Abductores", "Gemelos", "Hack"]
        torso = ["Press", "Jalón", "Remo", "Dominadas", "Smith", "Scott", "Pecho"]
        for m in gimnasio.maquinas:
            if m.tipo_maquina == "Musculacion":
                if any(p in m.nombre for p in pierna):
                    m.tipo_maquina = "Musculacion_Pierna"
                elif any(p in m.nombre for p in torso):
                    m.tipo_maquina = "Musculacion_Torso"
                else:
                    m.tipo_maquina = "Musculacion_Torso"

    def generar_flota_semanal(self, env, gimnasio, base_datos, semana_abs, factor):
        programados = []  # Los que van a ir físicamente
        lista_no_shows = []  # Los que reservaron y fallaron (para castigarlos luego)

        # --- 1. FILTRO DE ACCESO (EL PORTERO) ---
        socios_permitidos = []
        bloqueados_baja = 0
        bloqueados_castigo = 0

        for s in base_datos:
            # Si está dado de baja, NO ENTRA
            if not s.get("activo", True):
                bloqueados_baja += 1
                continue

            # Si está castigado esta semana, NO ENTRA
            # Ejemplo: Castigado hasta sem 5. Estamos en sem 4. (4 < 5) -> True -> Bloqueado.
            if s.get("castigado_hasta_semana_absoluta", 0) > semana_abs:
                bloqueados_castigo += 1
                continue

            socios_permitidos.append(s)

        cupo = int(self.config.CLIENTES_BASE * factor)
        print(
            f"   ℹ️ Acceso: {len(socios_permitidos)} permitidos | 🚫 Bloqueados: {bloqueados_baja} (Baja) / {bloqueados_castigo} (Castigo)")

        if not socios_permitidos: return [], []

        # --- 2. GENERACIÓN DE RESERVAS Y ASISTENCIA ---
        for dia_idx, nombre_dia in enumerate(self.config.DIAS_SEMANA):
            sesiones = self.config.obtener_sesiones_por_dia(nombre_dia)
            reservados_hoy = set()

            for sesion in range(sesiones):
                var = self.config.datos["simulacion"]["variacion_afluencia"]
                # Calculamos cuántos reservan plaza
                reservas_totales = int(random.uniform(1.0 - var, 1.0 + var) * cupo)

                # Elegimos quiénes reservan de los permitidos
                candidatos = [s for s in socios_permitidos if s['id'] not in reservados_hoy]
                if not candidatos: continue

                seleccionados = random.sample(candidatos, min(reservas_totales, len(candidatos)))
                inicio = (dia_idx * self.config.MINUTOS_MAXIMOS_POR_DIA) + (sesion * self.config.DURACION_SESION)

                for dato in seleccionados:
                    reservados_hoy.add(dato['id'])

                    # --- SIMULACIÓN DE "NO SHOW" (GENTE QUE FALLA) ---
                    # 5% de probabilidad de reservar y no ir
                    es_no_show = random.random() < 0.05

                    if es_no_show:
                        # Lo añadimos a la lista negra de esta semana
                        lista_no_shows.append(dato['id'])
                    else:
                        # Sí viene, creamos el usuario físico
                        u = Usuario(
                            id_usuario=dato["id"], nombre=dato["nombre"], tipo_usuario="Socio",
                            tiempo_llegada=inicio + random.uniform(0, 10), hora_fin=inicio + random.randint(60, 90),
                            rutina=dato["rutina"], perfil=PerfilGenerado(dato["perfil"]), problema=None,
                            config=self.config.datos, env=env, gimnasio=gimnasio,
                            faltas_consecutivas=dato["faltas_consecutivas"]
                        )
                        u.satisfaccion = dato.get("satisfaccion_acumulada", 100)
                        programados.append(u)

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

            u.process = env.process(u.entrenar(90))

    def gestor_semanal(self, env, admin_logs):
        for dia in self.config.DIAS_SEMANA:
            sesiones = self.config.obtener_sesiones_por_dia(dia)
            for i in range(1, sesiones + 1):
                admin_logs.cambiar_sesion(dia, i)
                yield env.timeout(self.config.DURACION_SESION)

            restante = (self.config.MINUTOS_MAXIMOS_POR_DIA - sesiones * self.config.DURACION_SESION)
            if restante > 0: yield env.timeout(restante)