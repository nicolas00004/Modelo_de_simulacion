import simpy
import random
from usuario import Usuario
from GestorSocios import PerfilGenerado


class MotorSimulacion:
    def __init__(self, config):
        self.config = config

    def clasificar_maquinas(self, gimnasio):
        pierna = ["Prensa", "Sentadilla", "Extensión", "Femoral", "Abductores"]
        torso = ["Press", "Jalón", "Remo", "Dominadas", "Smith"]
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
        activos = [s for s in base_datos if
                   s.get("activo", True) and s.get("castigado_hasta_semana_absoluta", 0) < semana_abs]
        cupo = int(self.config.CLIENTES_BASE * factor)
        print(f"   ℹ️ Activos: {len(activos)} | Cupo: ~{cupo}")

        if not activos: return []

        for dia_idx, nombre_dia in enumerate(self.config.DIAS_SEMANA):
            sesiones = self.config.obtener_sesiones_por_dia(nombre_dia)
            reservados_hoy = set()
            for sesion in range(sesiones):
                var = self.config.datos["simulacion"]["variacion_afluencia"]
                asistentes = int(random.uniform(1.0 - var, 1.0 + var) * cupo)
                candidatos = [s for s in activos if s['id'] not in reservados_hoy]
                if not candidatos: continue

                seleccionados = random.sample(candidatos, min(asistentes, len(candidatos)))
                inicio = (dia_idx * self.config.MINUTOS_MAXIMOS_POR_DIA) + (sesion * self.config.DURACION_SESION)

                for dato in seleccionados:
                    reservados_hoy.add(dato['id'])
                    u = Usuario(
                        id_usuario=dato["id"], nombre=dato["nombre"], tipo_usuario="Socio",
                        tiempo_llegada=inicio + random.uniform(0, 10), hora_fin=inicio + random.randint(60, 90),
                        rutina=dato["rutina"], perfil=PerfilGenerado(dato["perfil"]), problema=None,
                        config=self.config.datos, env=env, gimnasio=gimnasio,
                        faltas_consecutivas=dato["faltas_consecutivas"]
                    )
                    u.satisfaccion = dato.get("satisfaccion_acumulada", 100)
                    programados.append(u)
        return programados

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

            u.process = env.process(u.entrenar(90))

    def gestor_semanal(self, env, admin_logs):
        for dia in self.config.DIAS_SEMANA:
            sesiones = self.config.obtener_sesiones_por_dia(dia)
            for i in range(1, sesiones + 1):
                admin_logs.cambiar_sesion(dia, i)
                yield env.timeout(self.config.DURACION_SESION)

            restante = (self.config.MINUTOS_MAXIMOS_POR_DIA - sesiones * self.config.DURACION_SESION)
            if restante > 0: yield env.timeout(restante)