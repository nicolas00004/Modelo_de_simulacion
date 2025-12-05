
import usuario

class Accesorios():
    def __init__(self, nombre:str,disponibilidad:bool,durabilidad:int,registro_usuario:list[usuario]):
        self.nombre = nombre
        self.disponibilidad = disponibilidad
        self.durabilidad = durabilidad
        self.registro_usuario = registro_usuario


    def sumar_usuario_registro(self, usuario: usuario.Usuario):
        self.registro_usuario.insert(usuario)

    def usar(self):
        self.disponibilidad=False
        self.durabilidad=self.durabilidad-1

    def liberar(self):
        self.disponibilidad=True