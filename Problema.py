import simpy


class Problema():
    def __init__(self, env: simpy.Environment,descripcion:str,id:int,tipo:str,tiempo_solcuion:int):
        self.descripcion = descripcion
        self.id = id
        self.tipo=tipo
        self.tiempo_solcuion = tiempo_solcuion
