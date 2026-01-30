# Changelog barras-tareas

## 2026-01-26 - Botones cerrar y borde azul

### Añadido
- **Cerrar Barras**: Botón que cierra todas las barras (archivos siguen abiertos)
- **Cerrar Barras y Archivos**: Botón que cierra barras Y envía WM_CLOSE a los archivos
- `barras.pyw`: Archivo lanzador sin consola (doble click para abrir)
- `crear_acceso_directo.py`: Script para crear acceso directo en escritorio

### Modificado
- **Borde azul uniforme**: Todas las barras tienen borde azul (#0078d4) de 4px

---

## 2026-01-26 - Colores contrastados y gestión de barras

### Añadido
- **Renombrar Barra**: Botón en gestor para cambiar nombre de barra existente
- **Eliminar Barra**: Botón en gestor para eliminar barra (con confirmación)
- `generar_color_archivo()`: Nueva función para colores con máximo contraste

### Corregido
- **Colores de archivos**: Ahora se distribuyen uniformemente en el círculo cromático (360°/n separación)
- **Botones superpuestos**: Limpieza más agresiva de widgets antes de recrear (removeWidget + hide + processEvents)

### Métodos nuevos/modificados
- `GestorBarras.renombrar_barra()`: Cambia nombre en config y actualiza título de ventana
- `GestorBarras.eliminar_barra()`: Cierra barra, desacopla si está en grupo, elimina de config
- `GestorBarras.migrar_colores()`: Ahora recalcula colores para máximo contraste
- `GestorBarras.agregar_archivo()`: Recalcula colores de TODOS los archivos de la barra al añadir uno nuevo

---

## 2026-01-26 - Sistema de colores, escala y acoplamiento

### Añadido
- **Sistema de colores**: Cada barra tiene borde de color único, cada botón/archivo tiene fondo de color único
- **Escala configurable**: Slider en gestor (1.0x - 2.5x), default 1.4x, actualiza barras en tiempo real
- **Acoplamiento de barras**: Arrastrar cerca de otra barra las acopla, se mueven juntas
- **Snap a taskbar**: Arrastrar a esquina inferior izquierda/derecha ancla la barra
- **Desacoplamiento**: Alejar barra >50px del grupo la desacopla
- **Persistencia de grupos**: Los acoplamientos se guardan en config.json

### Modificado
- Gestor duplicado a 600x300 px
- Click simplificado: toggle directo minimizar/restaurar (sin menú contextual)
- Migración automática: config.json antiguo recibe colores automáticamente

### Funciones auxiliares añadidas
- `generar_color_unico(indice)`: HSL saturado distribuido uniformemente
- `color_contraste(hsl_color)`: Retorna blanco/negro según luminosidad
- `hsl_to_hex(hsl_color)`: Convierte HSL string a hex

### Constantes de escala (líneas 29-36)
```python
BASE_BUTTON_PADDING_V = 8
BASE_BUTTON_PADDING_H = 16
BASE_FONT_SIZE = 12
BASE_MARGIN = 4
BASE_BORDER_RADIUS = 4
BASE_CONTAINER_MARGIN = 8
DEFAULT_SCALE = 1.4
```

### Estructura config.json actualizada
```json
{
  "escala": 1.4,
  "grupos": [["barra1", "barra2"]],
  "barras": [
    {
      "nombre": "...",
      "color_borde": "hsl(0, 70%, 45%)",
      "posicion": {"x": 100, "y": 100},
      "archivos": [
        {"path": "...", "orden": 1, "color": "hsl(100, 70%, 45%)"}
      ]
    }
  ]
}
```

### APIs Windows añadidas
- `win32api.GetMonitorInfo()`: Obtener área de trabajo (excluye taskbar)
- `win32api.MonitorFromPoint()`: Detectar monitor principal

### Métodos clave nuevos
- `BarraArchivos.aplicar_estilos()`: Aplica escala y color de borde
- `BarraArchivos.mouseReleaseEvent()`: Verifica snap/acoplamiento al soltar
- `GestorBarras.verificar_snap_y_acoplamiento()`: Lógica principal de anclaje
- `GestorBarras.acoplar_barras()`: Une barras en grupo
- `GestorBarras.desacoplar_barra()`: Separa barra del grupo
- `GestorBarras.migrar_colores()`: Añade colores a config antigua
