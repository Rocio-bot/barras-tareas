"""
Prototipo: Barras de tareas personalizadas para Windows
Requiere: pip install PyQt5 pywin32 psutil

Hotkeys/funcionalidad:
- Click en botón: toggle minimizar/restaurar ventana
- Arrastrar barra: mover libremente
- Arrastrar cerca de taskbar: snap a esquina izquierda/derecha
- Arrastrar barras juntas: se acoplan y mueven como grupo
"""

import sys
import os
import json
import psutil
import win32gui
import win32con
import win32process
import win32api
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QPushButton, QMessageBox,
    QSystemTrayIcon, QInputDialog, QFileDialog, QSlider, QLabel, QVBoxLayout,
    QScrollArea, QFrame, QGroupBox, QMenu, QAction
)
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtGui import QIcon, QColor

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# Constantes base (se multiplican por SCALE_FACTOR)
BASE_BUTTON_PADDING_V = 8
BASE_BUTTON_PADDING_H = 16
BASE_FONT_SIZE = 12
BASE_MARGIN = 4
BASE_BORDER_RADIUS = 4
BASE_CONTAINER_MARGIN = 8
DEFAULT_SCALE = 1.4

# Umbrales para snap/acoplamiento
SNAP_THRESHOLD = 30  # Pixels para detectar cercanía a taskbar
DOCK_THRESHOLD = 20  # Pixels para acoplar barras entre sí
UNDOCK_THRESHOLD = 50  # Pixels para desacoplar barra del grupo


def generar_color_unico(indice):
    """Genera color HSL saturado para barras (distribuido con primo 37)"""
    hue = (indice * 37) % 360
    return f"hsl({hue}, 70%, 45%)"


def generar_color_archivo(indice_archivo, total_archivos, hue_base=0):
    """Genera color para archivo, máximo contraste entre archivos de misma barra.

    Distribuye colores uniformemente en el círculo cromático.
    indice_archivo: 0, 1, 2...
    total_archivos: cuántos archivos hay en la barra
    hue_base: offset para que cada barra tenga paleta diferente
    """
    if total_archivos <= 1:
        separacion = 0
    else:
        separacion = 360 // total_archivos

    hue = (hue_base + indice_archivo * separacion) % 360
    return f"hsl({hue}, 75%, 45%)"


def color_contraste(hsl_color):
    """Retorna blanco o negro según la luminosidad del color HSL"""
    # Extraer luminosidad del string hsl(h, s%, l%)
    try:
        parts = hsl_color.replace("hsl(", "").replace(")", "").replace("%", "").split(",")
        lightness = int(parts[2].strip())
        return "#ffffff" if lightness < 55 else "#000000"
    except:
        return "#ffffff"


def hsl_to_hex(hsl_color):
    """Convierte color HSL string a hex para bordes"""
    try:
        parts = hsl_color.replace("hsl(", "").replace(")", "").replace("%", "").split(",")
        h = int(parts[0].strip())
        s = int(parts[1].strip()) / 100
        l = int(parts[2].strip()) / 100

        # Conversión HSL a RGB
        if s == 0:
            r = g = b = l
        else:
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h/360 + 1/3)
            g = hue_to_rgb(p, q, h/360)
            b = hue_to_rgb(p, q, h/360 - 1/3)

        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    except:
        return "#3498db"


class BarraArchivos(QWidget):
    # Referencia global al gestor para acceder a grupos
    gestor = None

    def __init__(self, nombre_barra, archivos_config, color_borde=None, barra_index=0):
        super().__init__()
        self.nombre_barra = nombre_barra
        self.archivos_config = archivos_config
        self.color_borde = color_borde or generar_color_unico(barra_index)
        self.barra_index = barra_index
        self.ventanas_abiertas = {}
        self.drag_position = None

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
        self.aplicar_estilos()

        self.layout = QHBoxLayout()
        scale = self.get_scale()
        margin = int(BASE_CONTAINER_MARGIN * scale)
        self.layout.setContentsMargins(margin, margin, margin, margin)
        self.setLayout(self.layout)

        self.botones = {}

    def get_scale(self):
        """Obtiene el factor de escala del gestor"""
        if BarraArchivos.gestor and hasattr(BarraArchivos.gestor, 'config'):
            return BarraArchivos.gestor.config.get("escala", DEFAULT_SCALE)
        return DEFAULT_SCALE

    def aplicar_estilos(self):
        """Aplica estilos con escala y borde azul"""
        scale = self.get_scale()
        padding_v = int(BASE_BUTTON_PADDING_V * scale)
        padding_h = int(BASE_BUTTON_PADDING_H * scale)
        font_size = int(BASE_FONT_SIZE * scale)
        margin = int(BASE_MARGIN * scale)
        border_radius = int(BASE_BORDER_RADIUS * scale)

        # Borde azul para todas las barras
        border_color = "#0078d4"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: #2d2d2d;
                border: 4px solid {border_color};
                border-radius: {border_radius + 4}px;
            }}
            QPushButton {{
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: {padding_v}px {padding_h}px;
                margin: {margin}px;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: #4d4d4d;
            }}
            QPushButton:pressed {{
                background-color: #5d5d5d;
            }}
        """)

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
                    titulo_lower = titulo.lower()
                    for archivo in self.archivos_config:
                        nombre_archivo = os.path.basename(archivo["path"])
                        nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
                        # Buscar nombre al inicio del título (más preciso)
                        # Ej: "adjunto.txt - Notepad++" o "adjunto - Bloc de notas"
                        if (titulo_lower.startswith(nombre_archivo.lower()) or
                            titulo_lower.startswith(nombre_sin_ext.lower() + " ") or
                            titulo_lower.startswith(nombre_sin_ext.lower() + "-") or
                            titulo_lower.startswith("*" + nombre_archivo.lower()) or
                            titulo_lower.startswith("*" + nombre_sin_ext.lower())):
                            archivos_abiertos[archivo["path"]] = hwnd
            return True

        win32gui.EnumWindows(callback, None)

        self.ventanas_abiertas = archivos_abiertos
        self.actualizar_botones()

    def actualizar_botones(self):
        """Muestra solo los archivos abiertos, en orden configurado"""
        # Limpiar botones existentes completamente
        for btn in self.botones.values():
            self.layout.removeWidget(btn)
            btn.hide()
            btn.setParent(None)
            btn.deleteLater()
        self.botones.clear()

        # Procesar eventos pendientes para asegurar limpieza
        QApplication.processEvents()

        archivos_ordenados = sorted(
            [a for a in self.archivos_config if a["path"] in self.ventanas_abiertas],
            key=lambda x: x.get("orden", 999)
        )

        scale = self.get_scale()
        padding_v = int(BASE_BUTTON_PADDING_V * scale)
        padding_h = int(BASE_BUTTON_PADDING_H * scale)
        font_size = int(BASE_FONT_SIZE * scale)
        margin = int(BASE_MARGIN * scale)
        border_radius = int(BASE_BORDER_RADIUS * scale)

        for archivo in archivos_ordenados:
            path = archivo["path"]
            nombre = os.path.basename(path)
            color = archivo.get("color", "#3d3d3d")
            texto_color = color_contraste(color) if color.startswith("hsl") else "#ffffff"

            # Convertir HSL a hex para el fondo del botón
            bg_color = hsl_to_hex(color) if color.startswith("hsl") else color

            btn = QPushButton(nombre)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: {texto_color};
                    border: none;
                    padding: {padding_v}px {padding_h}px;
                    margin: {margin}px;
                    border-radius: {border_radius}px;
                    font-size: {font_size}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    filter: brightness(1.2);
                    background-color: {bg_color};
                    opacity: 0.8;
                }}
                QPushButton:pressed {{
                    background-color: {bg_color};
                }}
            """)
            btn.clicked.connect(lambda checked, p=path: self.toggle_ventana(p))
            self.layout.addWidget(btn)
            self.botones[path] = btn

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

        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    def mousePressEvent(self, event):
        """Permite arrastrar la barra"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Arrastra la barra (y grupo si está acoplada)"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            new_pos = event.globalPos() - self.drag_position

            # Verificar si pertenece a un grupo
            if BarraArchivos.gestor:
                grupo = BarraArchivos.gestor.obtener_grupo(self)
                if grupo and len(grupo) > 1:
                    # Calcular delta de movimiento
                    delta = new_pos - self.pos()
                    # Mover todas las barras del grupo
                    for barra in grupo:
                        barra.move(barra.pos() + delta)
                else:
                    self.move(new_pos)
            else:
                self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Al soltar, verificar snap a taskbar o acoplamiento con otras barras"""
        if event.button() == Qt.LeftButton:
            if BarraArchivos.gestor:
                BarraArchivos.gestor.verificar_snap_y_acoplamiento(self)
            event.accept()


class GestorBarras(QWidget):
    def __init__(self):
        super().__init__()
        self.barras = []
        self.grupos_acoplados = []  # [[barra1, barra2], [barra3]]
        self.config = self.cargar_config()

        # Establecer referencia global
        BarraArchivos.gestor = self

        # Servidor local para detectar segunda instancia
        self.local_server = QLocalServer(self)
        self.local_server.newConnection.connect(self.nueva_conexion_local)
        # Limpiar servidor anterior si quedó bloqueado
        QLocalServer.removeServer("BarrasTareasApp")
        self.local_server.listen("BarrasTareasApp")

        # Obtener área de trabajo (excluye taskbar)
        self.obtener_area_trabajo()

        self.init_ui()
        self.crear_barras()

    def nueva_conexion_local(self):
        """Otra instancia quiere abrir el gestor"""
        socket = self.local_server.nextPendingConnection()
        if socket:
            socket.deleteLater()
        self.mostrar_gestor()


    def obtener_area_trabajo(self):
        """Obtiene el área de trabajo del monitor principal"""
        try:
            monitor = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
            self.work_area = monitor['Work']  # (left, top, right, bottom)
            self.screen_area = monitor['Monitor']
        except:
            # Fallback
            self.work_area = (0, 0, 1920, 1040)
            self.screen_area = (0, 0, 1920, 1080)

    def init_ui(self):
        self.setWindowTitle("Gestor de Barras")
        self.setFixedSize(650, 550)
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
            QSlider::groove:horizontal {
                height: 8px;
                background: #3d3d3d;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QLabel {
                font-size: 14px;
            }
            QScrollArea {
                border: none;
                background-color: #252530;
            }
        """)

        main_layout = QVBoxLayout()

        # Fila 1: Crear y agregar
        buttons_layout1 = QHBoxLayout()

        btn_nueva_barra = QPushButton("Nueva Barra")
        btn_nueva_barra.clicked.connect(self.crear_nueva_barra)
        buttons_layout1.addWidget(btn_nueva_barra)

        btn_agregar_archivo = QPushButton("Agregar Archivo")
        btn_agregar_archivo.clicked.connect(self.agregar_archivo)
        buttons_layout1.addWidget(btn_agregar_archivo)

        main_layout.addLayout(buttons_layout1)

        # Fila 2: Renombrar y eliminar
        buttons_layout2 = QHBoxLayout()

        btn_renombrar = QPushButton("Renombrar Barra")
        btn_renombrar.clicked.connect(self.renombrar_barra)
        buttons_layout2.addWidget(btn_renombrar)

        btn_eliminar = QPushButton("Eliminar Barra")
        btn_eliminar.clicked.connect(self.eliminar_barra)
        buttons_layout2.addWidget(btn_eliminar)

        main_layout.addLayout(buttons_layout2)

        # Fila 3: Cerrar barras
        buttons_layout3 = QHBoxLayout()

        btn_cerrar_barras = QPushButton("Cerrar Barras")
        btn_cerrar_barras.clicked.connect(self.cerrar_barras)
        buttons_layout3.addWidget(btn_cerrar_barras)

        btn_cerrar_todo = QPushButton("Cerrar Barras y Archivos")
        btn_cerrar_todo.clicked.connect(self.cerrar_barras_y_archivos)
        buttons_layout3.addWidget(btn_cerrar_todo)

        main_layout.addLayout(buttons_layout3)

        # Control de escala
        scale_layout = QHBoxLayout()

        self.scale_label = QLabel(f"Escala: {self.config.get('escala', DEFAULT_SCALE):.1f}x")
        scale_layout.addWidget(self.scale_label)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setMinimum(10)  # 1.0x
        self.scale_slider.setMaximum(25)  # 2.5x
        self.scale_slider.setValue(int(self.config.get('escala', DEFAULT_SCALE) * 10))
        self.scale_slider.valueChanged.connect(self.cambiar_escala)
        scale_layout.addWidget(self.scale_slider)

        main_layout.addLayout(scale_layout)

        # Panel de listado de barras (fondo diferente)
        listado_label = QLabel("Barras configuradas:")
        listado_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(listado_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(250)

        self.listado_widget = QWidget()
        self.listado_widget.setStyleSheet("background-color: #252530;")
        self.listado_layout = QVBoxLayout()
        self.listado_layout.setAlignment(Qt.AlignTop)
        self.listado_widget.setLayout(self.listado_layout)

        self.scroll_area.setWidget(self.listado_widget)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

        # Poblar listado inicial
        self.actualizar_listado_barras()

    def actualizar_listado_barras(self):
        """Actualiza el panel con el listado de barras y sus archivos"""
        # Limpiar listado existente
        while self.listado_layout.count():
            child = self.listado_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for barra_config in self.config.get("barras", []):
            # Contenedor para cada barra
            barra_frame = QFrame()
            barra_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d3a;
                    border: 1px solid #0078d4;
                    border-radius: 6px;
                    margin: 4px;
                    padding: 8px;
                }
            """)
            barra_layout = QVBoxLayout()
            barra_layout.setContentsMargins(8, 8, 8, 8)
            barra_layout.setSpacing(4)

            # Nombre de la barra
            nombre_label = QLabel(f"  {barra_config['nombre']}")
            nombre_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #0078d4;")
            barra_layout.addWidget(nombre_label)

            # Archivos de la barra
            for archivo in barra_config.get("archivos", []):
                path = archivo["path"]
                nombre = os.path.basename(path)
                color = archivo.get("color", "#3d3d3d")

                # Convertir HSL a hex para el botón
                bg_color = hsl_to_hex(color) if color.startswith("hsl") else color
                texto_color = color_contraste(color) if color.startswith("hsl") else "#ffffff"

                btn_archivo = QPushButton(f"  {nombre}")
                btn_archivo.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: {texto_color};
                        border: none;
                        padding: 6px 12px;
                        margin: 2px 0;
                        border-radius: 4px;
                        text-align: left;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        opacity: 0.8;
                        border: 1px solid white;
                    }}
                """)
                btn_archivo.setToolTip(path)
                btn_archivo.clicked.connect(lambda checked, p=path: self.abrir_archivo(p))
                barra_layout.addWidget(btn_archivo)

            barra_frame.setLayout(barra_layout)
            self.listado_layout.addWidget(barra_frame)

    def abrir_archivo(self, path):
        """Abre un archivo o carpeta con la aplicación predeterminada"""
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{path}\n\n{e}")

    def cambiar_escala(self, value):
        """Actualiza la escala y refresca todas las barras"""
        escala = value / 10.0
        self.config['escala'] = escala
        self.scale_label.setText(f"Escala: {escala:.1f}x")
        self.guardar_config()

        # Actualizar todas las barras
        for barra in self.barras:
            barra.aplicar_estilos()
            margin = int(BASE_CONTAINER_MARGIN * escala)
            barra.layout.setContentsMargins(margin, margin, margin, margin)
            barra.actualizar_botones()

    def cargar_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Migración: añadir colores si faltan
                self.migrar_colores(config)
                return config
        return {"barras": [], "escala": DEFAULT_SCALE, "grupos": []}

    def migrar_colores(self, config):
        """Añade/recalcula colores para máximo contraste entre archivos de misma barra"""
        modificado = False

        for i, barra in enumerate(config.get("barras", [])):
            if "color_borde" not in barra:
                barra["color_borde"] = generar_color_unico(i)
                modificado = True

            # Recalcular colores de archivos para máximo contraste
            archivos = barra.get("archivos", [])
            total = len(archivos)
            hue_base = (i * 60) % 360  # Cada barra empieza en hue diferente

            for j, archivo in enumerate(archivos):
                nuevo_color = generar_color_archivo(j, total, hue_base)
                if archivo.get("color") != nuevo_color:
                    archivo["color"] = nuevo_color
                    modificado = True

        if "escala" not in config:
            config["escala"] = DEFAULT_SCALE
            modificado = True

        if "grupos" not in config:
            config["grupos"] = []
            modificado = True

        if modificado:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    def guardar_config(self):
        # Guardar grupos acoplados por nombre de barra
        grupos_nombres = []
        for grupo in self.grupos_acoplados:
            nombres = [b.nombre_barra for b in grupo]
            grupos_nombres.append(nombres)
        self.config["grupos"] = grupos_nombres

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def crear_barras(self):
        for i, barra_config in enumerate(self.config.get("barras", [])):
            barra = BarraArchivos(
                barra_config["nombre"],
                barra_config["archivos"],
                barra_config.get("color_borde"),
                i
            )
            if "posicion" in barra_config:
                barra.move(barra_config["posicion"]["x"], barra_config["posicion"]["y"])
            self.barras.append(barra)

        # Restaurar grupos acoplados desde config
        self.restaurar_grupos()

    def restaurar_grupos(self):
        """Restaura grupos acoplados desde la configuración"""
        for grupo_nombres in self.config.get("grupos", []):
            grupo = []
            for nombre in grupo_nombres:
                for barra in self.barras:
                    if barra.nombre_barra == nombre:
                        grupo.append(barra)
                        break
            if len(grupo) > 1:
                self.grupos_acoplados.append(grupo)

    def obtener_grupo(self, barra):
        """Retorna el grupo al que pertenece la barra, o [barra] si no está acoplada"""
        for grupo in self.grupos_acoplados:
            if barra in grupo:
                return grupo
        return [barra]

    def verificar_snap_y_acoplamiento(self, barra):
        """Verifica si la barra debe hacer snap a taskbar o acoplarse a otra"""
        pos = barra.pos()
        barra_rect = barra.geometry()

        # 1. Verificar snap a taskbar (borde inferior)
        work_bottom = self.work_area[3]

        # Zona izquierda de taskbar
        if pos.y() + barra_rect.height() > work_bottom - SNAP_THRESHOLD:
            if pos.x() < SNAP_THRESHOLD + self.work_area[0]:
                # Snap a esquina inferior izquierda
                barra.move(self.work_area[0], work_bottom - barra_rect.height())
                return
            elif pos.x() + barra_rect.width() > self.work_area[2] - SNAP_THRESHOLD:
                # Snap a esquina inferior derecha
                barra.move(self.work_area[2] - barra_rect.width(), work_bottom - barra_rect.height())
                return

        # 2. Verificar acoplamiento con otras barras
        for otra in self.barras:
            if otra == barra:
                continue
            if not otra.isVisible():
                continue

            otra_rect = otra.geometry()

            # Detectar cercanía horizontal (barras lado a lado)
            if abs(pos.x() + barra_rect.width() - otra_rect.x()) < DOCK_THRESHOLD:
                # Acoplar a la izquierda de otra
                barra.move(otra_rect.x() - barra_rect.width(), otra_rect.y())
                self.acoplar_barras(barra, otra)
                return
            elif abs(pos.x() - (otra_rect.x() + otra_rect.width())) < DOCK_THRESHOLD:
                # Acoplar a la derecha de otra
                barra.move(otra_rect.x() + otra_rect.width(), otra_rect.y())
                self.acoplar_barras(barra, otra)
                return

            # Detectar cercanía vertical (barras arriba/abajo)
            if abs(pos.y() + barra_rect.height() - otra_rect.y()) < DOCK_THRESHOLD:
                if abs(pos.x() - otra_rect.x()) < DOCK_THRESHOLD:
                    # Acoplar arriba de otra
                    barra.move(otra_rect.x(), otra_rect.y() - barra_rect.height())
                    self.acoplar_barras(barra, otra)
                    return
            elif abs(pos.y() - (otra_rect.y() + otra_rect.height())) < DOCK_THRESHOLD:
                if abs(pos.x() - otra_rect.x()) < DOCK_THRESHOLD:
                    # Acoplar debajo de otra
                    barra.move(otra_rect.x(), otra_rect.y() + otra_rect.height())
                    self.acoplar_barras(barra, otra)
                    return

        # 3. Verificar desacoplamiento (si se aleja del grupo)
        grupo_actual = self.obtener_grupo(barra)
        if len(grupo_actual) > 1:
            # Calcular distancia al grupo
            for otra in grupo_actual:
                if otra == barra:
                    continue
                otra_rect = otra.geometry()
                # Si está muy lejos, desacoplar
                dist_x = abs(pos.x() - otra_rect.x())
                dist_y = abs(pos.y() - otra_rect.y())
                if dist_x > UNDOCK_THRESHOLD + barra_rect.width() or dist_y > UNDOCK_THRESHOLD + barra_rect.height():
                    self.desacoplar_barra(barra)
                    return

    def acoplar_barras(self, barra1, barra2):
        """Acopla dos barras en el mismo grupo"""
        grupo1 = None
        grupo2 = None

        for grupo in self.grupos_acoplados:
            if barra1 in grupo:
                grupo1 = grupo
            if barra2 in grupo:
                grupo2 = grupo

        if grupo1 is None and grupo2 is None:
            # Crear nuevo grupo
            self.grupos_acoplados.append([barra1, barra2])
        elif grupo1 is None:
            # Añadir barra1 al grupo de barra2
            grupo2.append(barra1)
        elif grupo2 is None:
            # Añadir barra2 al grupo de barra1
            grupo1.append(barra2)
        elif grupo1 != grupo2:
            # Fusionar grupos
            grupo1.extend(grupo2)
            self.grupos_acoplados.remove(grupo2)

        self.guardar_config()

    def desacoplar_barra(self, barra):
        """Desacopla una barra de su grupo"""
        for grupo in self.grupos_acoplados:
            if barra in grupo:
                grupo.remove(barra)
                if len(grupo) < 2:
                    self.grupos_acoplados.remove(grupo)
                self.guardar_config()
                return

    def crear_nueva_barra(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Barra", "Nombre de la barra:")
        if ok and nombre:
            indice = len(self.config["barras"])
            color_borde = generar_color_unico(indice)

            nueva_barra = {
                "nombre": nombre,
                "archivos": [],
                "posicion": {"x": 100, "y": 100},
                "color_borde": color_borde
            }
            self.config["barras"].append(nueva_barra)
            self.guardar_config()

            barra = BarraArchivos(nombre, [], color_borde, indice)
            barra.move(100, 100)
            self.barras.append(barra)
            self.actualizar_listado_barras()

    def agregar_archivo(self):
        if not self.config["barras"]:
            return

        nombres = [b["nombre"] for b in self.config["barras"]]
        barra_nombre, ok = QInputDialog.getItem(
            self, "Seleccionar Barra", "Barra:", nombres, 0, False
        )
        if not ok:
            return

        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo")
        if not archivo:
            return

        for i, barra_config in enumerate(self.config["barras"]):
            if barra_config["nombre"] == barra_nombre:
                orden = len(barra_config["archivos"]) + 1

                barra_config["archivos"].append({
                    "path": archivo,
                    "orden": orden,
                    "color": ""  # Se recalcula abajo
                })

                # Recalcular colores de TODOS los archivos para máximo contraste
                total = len(barra_config["archivos"])
                hue_base = (i * 60) % 360
                for j, arch in enumerate(barra_config["archivos"]):
                    arch["color"] = generar_color_archivo(j, total, hue_base)

                self.guardar_config()
                self.barras[i].archivos_config = barra_config["archivos"]
                self.actualizar_listado_barras()
                break

    def renombrar_barra(self):
        """Permite cambiar el nombre de una barra existente"""
        if not self.config["barras"]:
            return

        nombres = [b["nombre"] for b in self.config["barras"]]
        barra_actual, ok = QInputDialog.getItem(
            self, "Renombrar Barra", "Selecciona barra:", nombres, 0, False
        )
        if not ok:
            return

        nuevo_nombre, ok = QInputDialog.getText(
            self, "Renombrar Barra", "Nuevo nombre:", text=barra_actual
        )
        if not ok or not nuevo_nombre or nuevo_nombre == barra_actual:
            return

        # Actualizar en config y en la barra
        for i, barra_config in enumerate(self.config["barras"]):
            if barra_config["nombre"] == barra_actual:
                barra_config["nombre"] = nuevo_nombre
                self.barras[i].nombre_barra = nuevo_nombre
                self.barras[i].setWindowTitle(nuevo_nombre)
                self.guardar_config()
                self.actualizar_listado_barras()
                break

    def eliminar_barra(self):
        """Elimina una barra completamente"""
        if not self.config["barras"]:
            return

        nombres = [b["nombre"] for b in self.config["barras"]]
        barra_nombre, ok = QInputDialog.getItem(
            self, "Eliminar Barra", "Selecciona barra a eliminar:", nombres, 0, False
        )
        if not ok:
            return

        # Confirmar eliminación
        respuesta = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar la barra '{barra_nombre}' y todos sus archivos configurados?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if respuesta != QMessageBox.Yes:
            return

        # Buscar índice y eliminar
        for i, barra_config in enumerate(self.config["barras"]):
            if barra_config["nombre"] == barra_nombre:
                # Cerrar y eliminar la barra visual
                self.barras[i].timer.stop()
                self.barras[i].close()

                # Quitar de grupos acoplados si está
                self.desacoplar_barra(self.barras[i])

                # Eliminar de listas
                del self.barras[i]
                del self.config["barras"][i]

                self.guardar_config()
                self.actualizar_listado_barras()
                break

    def cerrar_barras(self):
        """Cierra todas las barras y la aplicación (archivos siguen abiertos)"""
        self.close()

    def cerrar_barras_y_archivos(self):
        """Cierra barras, aplicación Y los archivos abiertos"""
        # Recopilar ventanas de archivos a cerrar
        ventanas_a_cerrar = []
        for barra in self.barras:
            for hwnd in barra.ventanas_abiertas.values():
                if hwnd not in ventanas_a_cerrar:
                    ventanas_a_cerrar.append(hwnd)

        # Cerrar los archivos (enviar WM_CLOSE a cada ventana)
        for hwnd in ventanas_a_cerrar:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except:
                pass

        self.close()

    def closeEvent(self, event):
        """Al cerrar el gestor, cerrar todo"""
        self.guardar_posiciones()
        for barra in self.barras:
            barra.timer.stop()
            barra.close()
        event.accept()

    def guardar_posiciones(self):
        """Guarda las posiciones actuales de las barras"""
        for i, barra in enumerate(self.barras):
            if i < len(self.config["barras"]):
                pos = barra.pos()
                self.config["barras"][i]["posicion"] = {"x": pos.x(), "y": pos.y()}
        self.guardar_config()


def main():
    app = QApplication(sys.argv)

    # Verificar si ya hay una instancia corriendo
    socket = QLocalSocket()
    socket.connectToServer("BarrasTareasApp")
    if socket.waitForConnected(500):
        # Ya hay otra instancia, enviar señal y salir
        socket.disconnectFromServer()
        return

    app.setQuitOnLastWindowClosed(False)

    gestor = GestorBarras()
    gestor.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
