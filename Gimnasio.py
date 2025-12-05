import usuario
import Maquina
import Monitor
from usuario import Usuario


class Gimnasio:
    def __init__(self, maquinas: list[Maquina], monitores: list[Monitor],list[Accesorios], capacidad,n_usuarios):
        self.maquinas = maquinas
        self.monitores = monitores
        self.capacidad = capacidad
        self.n_usuarios=n_usuarios

    def abrir_gimnasio(self):
        print("hola")

    def cerrar_gimnasio(self):
        print ("hola")