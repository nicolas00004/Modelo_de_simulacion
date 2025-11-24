# Instrucciones

Para que el programa pueda sea ejecutable en cualquier entorno vamos a usar entornos virtuales de python (venv)
Lo iniciamos ejecutando

```
python3 -m venv venv
```

en la carpeta del proyecto. Con

```
source venv/bin/activate
```

lo activamos y con

```
deactivate
```

lo desactivamos. Es importante tenerlo activado siempre que vayamos a hacer cosas en el proyecto.

`requirements.txt` tiene los paquetes que se necesitan. Para instalarlos ejecutar

```
pip install -r requirements.txt
```

asegurandonos siempre de que tengamos el venv activado.
Cada vez que hagamos `pull` de github tenemos que hacer esto para tener los paquetes que hayan instalado otros.
Cada vez que instalemos un paquete nuevo tenemos que actualizar la lista ejecutando

```
pip3 freeze > requirements.txt
```

Cada vez que vayamos a hacer `push` a github tenemos que hacerlo para que los otros sepan que paquetes hemos instalado.
