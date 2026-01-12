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
| `config.json` | Configuración de barras y archivos (personal, no en GitHub) |
| `config.json.example` | Plantilla de configuración para repo público |
| `iniciar.bat` | Lanzador sin consola (`pythonw`) |
| `.gitignore` | Excluye `config.json` del repo para privacidad |

### Clases principales (`prototipo.py`)

**`BarraArchivos(QWidget)`** - Barra flotante individual
- Muestra botones solo para archivos configurados que estén abiertos
- Monitorea ventanas cada 2 segundos (`init_monitor`)
- Detecta archivos abiertos comparando títulos de ventana (`actualizar_estado`)
- Se oculta automáticamente si no hay archivos abiertos
- Arrastrable y siempre visible (on top)

**`GestorBarras(QWidget)`** - Ventana de administración
- Carga/guarda configuración JSON
- Crea instancias de `BarraArchivos`
- Interfaz para añadir barras y archivos
- Guarda posiciones al cerrar

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
  "barras": [
    {
      "nombre": "NombreBarra",
      "posicion": {"x": 100, "y": 100},
      "archivos": [
        {"path": "C:/ruta/archivo.xlsx", "orden": 1},
        {"path": "C:/ruta/otro.docx", "orden": 2}
      ]
    }
  ]
}
```

## Funcionalidades implementadas

- [x] Múltiples barras independientes
- [x] Orden personalizado de archivos
- [x] Click: toggle minimizar/restaurar/traer al frente
- [x] Click derecho: menú contextual (minimizar, maximizar)
- [x] Barras arrastrables
- [x] Siempre visibles (on top)
- [x] Auto-ocultar si no hay archivos abiertos
- [x] Persistencia de posición
- [x] Interfaz para añadir barras/archivos

## Limitaciones conocidas

1. **Detección por título**: Si el nombre del archivo no aparece en el título de ventana, no se detecta
2. **Apps con pestañas** (Chrome, VS Code): Detecta solo si el archivo está en la pestaña activa
3. **Sin iconos**: Los botones muestran solo texto, no iconos de archivo
4. **Sin indicador de foco**: No marca visualmente qué archivo está en primer plano

## APIs Windows utilizadas

```python
win32gui.EnumWindows()          # Listar todas las ventanas
win32gui.GetWindowText()        # Obtener título
win32gui.IsWindowVisible()      # Verificar si visible
win32gui.GetWindowPlacement()   # Estado (minimizado, normal, etc.)
win32gui.ShowWindow()           # Minimizar/restaurar
win32gui.SetForegroundWindow()  # Traer al frente
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

- **Barras más grandes**: Aumentar tamaño de botones y tipografía para mejor visibilidad
- **Colores por archivo**: Cada archivo con un color distinto para distinguirlos a simple vista
- Iconos reales extraídos del archivo/aplicación
- Indicador visual del archivo en primer plano
- Drag & drop para añadir archivos
- Reordenar arrastrando botones
- Tray icon para acceder al gestor
- Atajos de teclado
- Preview de ventana al hacer hover
