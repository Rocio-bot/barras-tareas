# Barras de Tareas - Uso Rápido

## Qué hace
Barras flotantes que muestran solo los archivos que configuras cuando están abiertos. Orden fijo por ti definido.

## Iniciar la app
**Doble click en:** `iniciar.bat`

## Usar
- **Click en botón**: minimiza/restaura/trae al frente el archivo
- **Click derecho**: menú minimizar/maximizar
- **Arrastrar barra**: moverla a otra posición
- La barra se oculta sola si no hay archivos abiertos

## Añadir archivos/barras
1. Cerrar la app (X en cualquier barra)
2. Abrir `config.json` con editor de texto
3. Añadir barras/archivos siguiendo estructura existente
4. Guardar y volver a abrir `iniciar.bat`

## Primera instalación
1. Copiar `config.json.example` a `config.json`
2. Editar `config.json` con tus rutas de archivos
3. Lanzar `iniciar.bat`

## Atajos
No hay atajos de teclado

## Requisitos
- Python 3
- PyQt5, pywin32, psutil

## Privacidad
- Tu `config.json` personal NO se sube a GitHub (excluido en `.gitignore`)
- Las rutas de tus archivos permanecen privadas
- Al actualizar desde GitHub (`git pull`), tu configuración se mantiene intacta
