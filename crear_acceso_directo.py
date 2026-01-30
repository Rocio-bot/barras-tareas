"""
Ejecuta este script UNA VEZ para crear un acceso directo en el escritorio.
Luego puedes borrar este archivo.
"""
import os
from win32com.client import Dispatch

# Rutas
carpeta_app = os.path.dirname(os.path.abspath(__file__))
archivo_pyw = os.path.join(carpeta_app, "barras.pyw")
escritorio = os.path.join(os.environ["USERPROFILE"], "Desktop")
acceso_directo = os.path.join(escritorio, "Gestor de Barras.lnk")

# Crear acceso directo
shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(acceso_directo)
shortcut.Targetpath = archivo_pyw
shortcut.WorkingDirectory = carpeta_app
shortcut.Description = "Gestor de Barras de Tareas"
shortcut.save()

print(f"Acceso directo creado en: {acceso_directo}")
print("Ahora puedes abrir 'Gestor de Barras' desde el escritorio.")
