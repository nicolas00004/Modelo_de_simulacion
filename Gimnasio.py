import usuario
import Maquina
import Monitor
from usuario import Usuario


class Gimansio:
    def __init__(self,maquinas: Maquina,monitor:Monitor,usuarios:Usuario):
        self.maquinas = maquinas
