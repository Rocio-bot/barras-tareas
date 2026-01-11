"""
Prototipo: Barras de tareas personalizadas para Windows
Requiere: pip install PyQt5 pywin32 psutil
"""

import sys
import os
import json
import psutil
import win32gui
import win32con
import win32process
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QPushButton,
    QMenu, QAction, QSystemTrayIcon, QInputDialog, QFileDialog
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon, QCursor

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

class BarraArchivos(QWidget):
    def __init__(self, nombre_barra, archivos_config):
        super().__init__()
        self.nombre_barra = nombre_barra
        self.archivos_config = archivos_config  # [{"path": "...", "orden": 1}, ...]
        self.ventanas_abiertas = {}  # {path: hwnd}

        self.init_ui()
        self.init_monitor()

    def init_ui(self):
        self.setWindowTitle(self.nombre_barra)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 8px 16px;
                margin: 4px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #5d5d5d;
            }
        """)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(self.layout)

        # Botones de archivos (se actualizan dinámicamente)
        self.botones = {}

    def init_monitor(self):
        """Monitorea cada 2 segundos qué archivos están abiertos"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_estado)
        self.timer.start(2000)
        self.actualizar_estado()

    def actualizar_estado(self):
        """Detecta qué archivos configurados están abiertos"""
        archivos_abiertos = {}

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                titulo = win32gui.GetWindowText(hwnd)
                if titulo:
                    for archivo in self.archivos_config:
                        nombre_archivo = os.path.basename(archivo["path"])
                        if nombre_archivo.lower() in titulo.lower():
                            archivos_abiertos[archivo["path"]] = hwnd
            return True

        win32gui.EnumWindows(callback, None)

        self.ventanas_abiertas = archivos_abiertos
        self.actualizar_botones()

    def actualizar_botones(self):
        """Muestra solo los archivos abiertos, en orden configurado"""
        # Limpiar botones existentes
        for btn in self.botones.values():
            btn.setParent(None)
            btn.deleteLater()
        self.botones.clear()

        # Ordenar por el campo "orden"
        archivos_ordenados = sorted(
            [a for a in self.archivos_config if a["path"] in self.ventanas_abiertas],
            key=lambda x: x.get("orden", 999)
        )

        # Crear botones para archivos abiertos
        for archivo in archivos_ordenados:
            path = archivo["path"]
            nombre = os.path.basename(path)
            btn = QPushButton(nombre)
            btn.clicked.connect(lambda checked, p=path: self.toggle_ventana(p))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, p=path: self.mostrar_menu(p)
            )
            self.layout.addWidget(btn)
            self.botones[path] = btn

        # Ocultar barra si no hay archivos abiertos
        if self.botones:
            self.adjustSize()
            self.show()
        else:
            self.hide()

    def toggle_ventana(self, path):
        """Minimiza o restaura la ventana del archivo"""
        hwnd = self.ventanas_abiertas.get(path)
        if not hwnd:
            return

        # Verificar si está minimizada
        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            # Restaurar
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        else:
            # Verificar si está en primer plano
            if win32gui.GetForegroundWindow() == hwnd:
                # Minimizar
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            else:
                # Traer al frente
                win32gui.SetForegroundWindow(hwnd)

    def mostrar_menu(self, path):
        """Menú contextual con opciones"""
        menu = QMenu()

        accion_minimizar = QAction("Minimizar", self)
        accion_minimizar.triggered.connect(lambda: self.minimizar(path))
        menu.addAction(accion_minimizar)

        accion_maximizar = QAction("Maximizar", self)
        accion_maximizar.triggered.connect(lambda: self.maximizar(path))
        menu.addAction(accion_maximizar)

        menu.exec_(QCursor.pos())

    def minimizar(self, path):
        hwnd = self.ventanas_abiertas.get(path)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    def maximizar(self, path):
        hwnd = self.ventanas_abiertas.get(path)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)

    def mousePressEvent(self, event):
        """Permite arrastrar la barra"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Arrastra la barra"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()


class GestorBarras(QWidget):
    def __init__(self):
        super().__init__()
        self.barras = []
        self.config = self.cargar_config()

        self.init_ui()
        self.crear_barras()

    def init_ui(self):
        self.setWindowTitle("Gestor de Barras")
        self.setFixedSize(300, 150)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px;
                margin: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
        """)

        layout = QHBoxLayout()

        btn_nueva_barra = QPushButton("Nueva Barra")
        btn_nueva_barra.clicked.connect(self.crear_nueva_barra)
        layout.addWidget(btn_nueva_barra)

        btn_agregar_archivo = QPushButton("Agregar Archivo")
        btn_agregar_archivo.clicked.connect(self.agregar_archivo)
        layout.addWidget(btn_agregar_archivo)

        self.setLayout(layout)

    def cargar_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"barras": []}

    def guardar_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def crear_barras(self):
        for barra_config in self.config.get("barras", []):
            barra = BarraArchivos(
                barra_config["nombre"],
                barra_config["archivos"]
            )
            # Posicionar si hay posición guardada
            if "posicion" in barra_config:
                barra.move(barra_config["posicion"]["x"], barra_config["posicion"]["y"])
            self.barras.append(barra)

    def crear_nueva_barra(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Barra", "Nombre de la barra:")
        if ok and nombre:
            nueva_barra = {
                "nombre": nombre,
                "archivos": [],
                "posicion": {"x": 100, "y": 100}
            }
            self.config["barras"].append(nueva_barra)
            self.guardar_config()

            barra = BarraArchivos(nombre, [])
            barra.move(100, 100)
            self.barras.append(barra)

    def agregar_archivo(self):
        if not self.config["barras"]:
            return

        # Seleccionar barra
        nombres = [b["nombre"] for b in self.config["barras"]]
        barra_nombre, ok = QInputDialog.getItem(
            self, "Seleccionar Barra", "Barra:", nombres, 0, False
        )
        if not ok:
            return

        # Seleccionar archivo
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo")
        if not archivo:
            return

        # Agregar a la configuración
        for i, barra_config in enumerate(self.config["barras"]):
            if barra_config["nombre"] == barra_nombre:
                orden = len(barra_config["archivos"]) + 1
                barra_config["archivos"].append({
                    "path": archivo,
                    "orden": orden
                })
                self.guardar_config()

                # Actualizar la barra existente
                self.barras[i].archivos_config = barra_config["archivos"]
                break

    def closeEvent(self, event):
        # Guardar posiciones antes de cerrar
        for i, barra in enumerate(self.barras):
            pos = barra.pos()
            self.config["barras"][i]["posicion"] = {"x": pos.x(), "y": pos.y()}
        self.guardar_config()

        for barra in self.barras:
            barra.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    gestor = GestorBarras()
    gestor.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
