import Tipo_Cola

class Maquina():
    def __int__(self,nombre:str,id:int,tipo_maquina:str,tipo_cola:Tipo_Cola,disponibilidad:bool,durabilidad:int):
        self.nombre = nombre
        self.id = id
        self.tipo_maquina = tipo_maquina
        self.tipo_cola = tipo_cola
        self.disponibilidad = disponibilidad
        self.durabilidad = durabilidad


    def romper(self):
        print("hello")
