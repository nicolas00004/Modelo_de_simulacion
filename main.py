import simpy
import time
import Gimnasio
import usuario
import Maquina
import Monitor
import json



def main():
    gimnasio = Gimnasio.Gimnasio()
    gimnasio.cargar_datos_json('datos_gimnasio.json')

    gimnasio.abrir_gimnasio()
    gimnasio.mostrar_resumen()
    gimnasio.cerrar_gimnasio()

    def clock(env, name, tick):
        while True:
            print(name, env.now)
            yield env.timeout(tick)

    env = simpy.Environment()
    env.process(clock(env, 'fast', 0.5))
    env.process(clock(env, 'slow', 1))
    env.run(until=2)


if __name__ == "__main__":
    main()