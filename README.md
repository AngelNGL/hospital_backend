### BACKEND HOSPITAL

En la terminal de python, para crear un entorno virtual, dentro del folder de "hospital_backend", corran:
>python -m venv .venv

Luego pongan:
>dir .venv

>.\\.venv\Scripts\activate

Si todo sale bien van a ver un ``(.venv)`` al inicio de los mensajes en la terminal.

Ya que esten ahi, corran:
>pip install -r requirements.txt

Y con eso ya estan listos para correr el servidor.

---
### COMO CORRERLO
Para correr el programa en servidor local:
>uvicorn app.main:app --reload --port 8010

---
### NOTA IMPORTANTE
Al pasar el documento, o subirlo a github, etc., no compartan el folder ``.venv/`` a menos que sea necesario.

Pesa demasiado como para estar moviendolo a todas partes.

---