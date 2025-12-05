import usuario
import Maquina
import Monitor
import Accesorios


class Gimnasio:
    def __init__(self, maquinas: list[Maquina], monitores: list[Monitor], accesorios:list[Accesorios],
                 capacidad, n_usuarios,usuarios_total,usuario: list[usuario]):
        self.maquinas = maquinas
        self.monitores = monitores
        self.capacidad = capacidad
        self.n_usuarios=n_usuarios
        self.accesorios = accesorios
        self.usuarios_total = usuarios_total
        self.usuario = usuario

    def abrir_gimnasio(self):
        print("hola")

    def cerrar_gimnasio(self):
        print ("hola")