# CLAUDE-barras-tareas.md

Guía técnica de la aplicación para Claude Code

**Repositorio GitHub:** https://github.com/Rocio-bot/barras-tareas

## Descripción

Barras de tareas personalizadas para Windows que reemplazan parcialmente la barra de tareas nativa. Permite organizar archivos abiertos en barras temáticas (ej: "Trabajo", "Contabilidad") con orden definido por la usuaria.

## Problema que resuelve

La barra de tareas de Windows muestra todos los archivos abiertos mezclados y en orden de apertura. Esta aplicación:
- Agrupa archivos por categorías
- Mantiene un orden fijo configurado
- Muestra solo los archivos que la usuaria decide monitorear

## Arquitectura

### Archivos

| Archivo | Función |
|---------|---------|
| `prototipo.py` | Aplicación principal (PyQt5) |
| `barras.pyw` | Lanzador sin consola (doble click para abrir) |
| `config.json` | Configuración de barras y archivos (personal, no en GitHub) |
| `config.json.example` | Plantilla de configuración para repo público |
| `iniciar.bat` | Lanzador alternativo sin consola |
| `crear_acceso_directo.py` | Ejecutar una vez para crear icono en escritorio |
| `.gitignore` | Excluye `config.json` del repo para privacidad |

### Clases principales (`prototipo.py`)

**`BarraArchivos(QWidget)`** - Barra flotante individual
- Muestra botones solo para archivos configurados que estén abiertos
- Monitorea ventanas cada 2 segundos (`init_monitor`)
- Detecta archivos abiertos comparando títulos de ventana (`actualizar_estado`)
- Se oculta automáticamente si no hay archivos abiertos
- Arrastrable y siempre visible (on top)
- Aplica escala y colores dinámicamente (`aplicar_estilos`)
- Al soltar, verifica snap/acoplamiento (`mouseReleaseEvent`)

**`GestorBarras(QWidget)`** - Ventana de administración
- Carga/guarda configuración JSON
- Crea instancias de `BarraArchivos`
- Interfaz para añadir barras y archivos
- Guarda posiciones al cerrar
- Slider de escala (1.0x - 2.5x) con actualización en tiempo real
- Gestiona grupos acoplados (`acoplar_barras`, `desacoplar_barra`)
- Snap a taskbar esquina izquierda/derecha
- Migración automática de configs antiguas (`migrar_colores`)

### Flujo de detección

```
Timer (2 seg) → EnumWindows → Comparar títulos → Actualizar botones → Show/Hide barra
```

La detección es por título de ventana: si el nombre del archivo aparece en el título, se considera abierto.

## Dependencias

```
PyQt5      # Interfaz gráfica
pywin32    # Control de ventanas Windows (win32gui, win32con)
psutil     # Info de procesos (poco usado actualmente)
```

## Estructura config.json

```json
{
  "escala": 1.4,
  "grupos": [["barra1", "barra2"]],
  "barras": [
    {
      "nombre": "NombreBarra",
      "color_borde": "hsl(0, 70%, 45%)",
      "posicion": {"x": 100, "y": 100},
      "archivos": [
        {"path": "C:/ruta/archivo.xlsx", "orden": 1, "color": "hsl(100, 70%, 45%)"},
        {"path": "C:/ruta/otro.docx", "orden": 2, "color": "hsl(137, 70%, 45%)"}
      ]
    }
  ]
}
```

## Funcionalidades implementadas

- [x] Múltiples barras independientes
- [x] Orden personalizado de archivos
- [x] Click: toggle minimizar/restaurar
- [x] Barras arrastrables
- [x] Siempre visibles (on top)
- [x] Auto-ocultar si no hay archivos abiertos
- [x] Persistencia de posición
- [x] Interfaz para añadir barras/archivos
- [x] **Renombrar barra**: Cambiar nombre desde el gestor
- [x] **Eliminar barra**: Borrar barra completa con confirmación
- [x] **Cerrar Barras**: Cierra todas las barras (archivos siguen abiertos)
- [x] **Cerrar Barras y Archivos**: Cierra barras y envía WM_CLOSE a archivos
- [x] **Borde azul**: Todas las barras tienen borde azul visible
- [x] **Colores únicos**: Borde de barra y fondo de botones con colores saturados
- [x] **Escala configurable**: Slider 1.0x-2.5x en gestor, actualización en tiempo real
- [x] **Acoplamiento de barras**: Arrastrar barras cerca las une, se mueven juntas
- [x] **Snap a taskbar**: Anclaje a esquinas inferiores izquierda/derecha
- [x] **Persistencia de grupos**: Los acoplamientos se guardan en config.json
- [x] **Migración automática**: Configs antiguas reciben colores y escala al cargar
- [x] **Instancia única**: Mutex impide abrir múltiples instancias; si ya hay una, la activa

## Limitaciones conocidas

1. **Detección por título**: Si el nombre del archivo no aparece en el título de ventana, no se detecta
2. **Apps con pestañas** (Chrome, VS Code): Detecta solo si el archivo está en la pestaña activa
3. **Sin iconos**: Los botones muestran solo texto, no iconos de archivo
4. **Sin indicador de foco**: No marca visualmente qué archivo está en primer plano
5. **Notepad++ y .txt**: Eliminada barra de archivos txt. Hipótesis: Notepad++ usa formato de título no estándar (quizás ruta completa o pestañas internas) que no coincide con la detección actual

## APIs Windows utilizadas

```python
win32gui.EnumWindows()          # Listar todas las ventanas
win32gui.GetWindowText()        # Obtener título
win32gui.IsWindowVisible()      # Verificar si visible
win32gui.GetWindowPlacement()   # Estado (minimizado, normal, etc.)
win32gui.ShowWindow()           # Minimizar/restaurar
win32gui.SetForegroundWindow()  # Traer al frente
win32api.GetMonitorInfo()       # Área de trabajo (excluye taskbar)
win32api.MonitorFromPoint()     # Detectar monitor principal
win32event.CreateMutex()        # Instancia única (evitar duplicados)
```

## Ejecución

```bash
# Desarrollo (con consola)
python prototipo.py

# Producción (sin consola)
pythonw prototipo.py
# o
iniciar.bat
```

## Configuración GitHub (repo público)

**Privacidad:**
- `config.json` está en `.gitignore` → NO se sube al repo
- Las rutas personales de archivos permanecen privadas
- `config.json.example` sirve como plantilla para otros usuarios
- Al hacer `git pull`, solo se actualizan archivos de código
- Tu `config.json` personal nunca se modifica por actualizaciones de GitHub

**Primera vez en nuevo equipo:**
1. Clonar repo: `git clone https://github.com/usuario/barras-tareas.git`
2. Copiar: `config.json.example` → `config.json`
3. Editar `config.json` con rutas personales
4. Lanzar `iniciar.bat`

## Posibles mejoras futuras

- Iconos reales extraídos del archivo/aplicación
- Indicador visual del archivo en primer plano
- Drag & drop para añadir archivos
- Reordenar arrastrando botones
- Tray icon para acceder al gestor
- Atajos de teclado
- Preview de ventana al hacer hover

---

## NOTAS PARA LA USUARIA

**Iniciar:** doble click en `barras.pyw` o en el acceso directo del escritorio

**Crear acceso directo:** ejecuta `python crear_acceso_directo.py` una sola vez

**Uso diario:**
- Click en botón → minimiza/restaura archivo
- Arrastrar barra → moverla
- Slider en gestor → ajustar tamaño de barras

**Gestionar barras:** botones en gestor: "Nueva Barra", "Renombrar", "Eliminar"

**Cerrar todo:**
- "Cerrar Barras" → cierra barras, archivos siguen abiertos
- "Cerrar Barras y Archivos" → cierra todo

**Añadir archivos:** botón "Agregar Archivo" o editar `config.json` (ver *Estructura config.json*)

**Tu config es privada:** ver *Configuración GitHub*
