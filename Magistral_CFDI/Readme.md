# Magistral CFDI 3.0.0 - Descarga Masiva de XML del SAT

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.0.0-red.svg)]()

**Desarrollado por Carlos Black**

---

##  Tabla de Contenido
- [Descripción General](#descripción-general)
- [Características](#características)
- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Guía de Uso](#guía-de-uso)
- [Tiempos de Descarga](#tiempos-de-descarga)
- [Solución de Problemas](#solución-de-problemas)
- [Crear Ejecutable](#crear-ejecutable)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Licencia](#licencia)
- [Contacto](#contacto)

---

## Descripción General

**Magistral CFDI 3.0.0** es una aplicación de escritorio desarrollada en Python con la librería PyQt6. Automatiza el proceso de autenticación, solicitud de descarga y verificación del estado de la solicitud de Comprobantes Fiscales Digitales por Internet (CFDI) desde el Servicio de Administración Tributaria (SAT) de México.

La aplicación permite descargar los CFDI **Emitidos** o **Recibidos** en un rango de fechas específico, con soporte para filtrado por estado y descarga paralela. Esta versión incluye una interfaz moderna con imágenes personalizadas, tabla de resultados y barra de progreso visual.

---

##  Características

### Generales:
-  Descarga de CFDIs **Emitidos** y **Recibidos**
-  Soporte para **CFDI (XML)** y **Metadata (JSON)**
-  Filtrado por estado: **Todos**, **Solo Vigentes**, **Solo Cancelados**
-  Validación automática de **RFC** y **FIEL**
-  Descarga **paralela** (3 hilos simultáneos)
-  Sistema de **logging** (`cfdi_downloader.log`)
-  Rango de fechas (máximo 1 año)

### Interfaz Moderna:
-  Tema visual Fusion
-  Imágenes personalizadas en botones (Descargar, Cancelar, Limpiar)
-  Tabla interactiva de resultados con archivos descargados
-  Barra de progreso visual
-  Tooltips informativos en cada campo
-  Selector intuitivo de formato (CFDI / Metadata)

---

##  Requisitos del Sistema

### Software:
- Windows 10/11 (64 bits)
- Python 3.8 o superior (para desarrollo)
- Conexión estable a Internet

### Dependencias:
```txt
PyQt6==6.9.1
cfdiclient==1.6.2
pyinstaller==6.11.1
```

---

##  Instalación

### Ejecutable 
1. Descargar el ejecutable desde [Releases](https://github.com/tuusuario/magistral-cfdi/releases)
2. Extraer el archivo `Magistral CFDI.zip`
3. Hacer doble clic en `Magistral CFDI.exe`

---

## Guía de Uso

### Pasos para descargar CFDIs:

1. **RFC del Contribuyente:** Ingresa tu Registro Federal de Contribuyentes (RFC)

2. **Archivos CER y KEY:**
   - Selecciona los archivos `.cer` y `.key` de tu FIEL
   - Utiliza los botones "📁" para buscar los archivos
   - **Importante:** Mantén estos archivos seguros

3. **Contraseña de la FIEL:** Ingresa la contraseña

4. **Carpeta de Descarga:** Selecciona dónde guardar los archivos ZIP

5. **Tipo de Descarga:**
   - **Emitidos:** CFDI que tú has emitido
   - **Recibidos:** CFDI que has recibido

6. **Formato:**
   - **CFDI (XML):** Obtiene los XML completos (solo vigentes en recibidos)
   - **Metadata (JSON):** Obtiene metadatos (incluye cancelados en recibidos)

7. **Estado CFDI:**
   - **Todos:** Descarga todos los CFDIs
   - **Solo Vigentes:** Solo CFDIs vigentes
   - **Solo Cancelados:** Solo CFDIs cancelados

8. **Rango de Fechas:**
   - Formato: `YYYY-MM-DD` (Ejemplo: 2026-03-01)
   - Máximo 1 año de diferencia

9. **Iniciar Descarga:** Haz clic en el botón "DESCARGAR" (imagen verde)

10. **Seguimiento:**
    - El panel "ESTADO DE DESCARGA" mostrará el progreso en tiempo real
    - La barra de progreso se actualizará automáticamente

11. **Resultados:**
    - Al finalizar, aparecerá una tabla con los archivos descargados
    - Cada archivo muestra su nombre y fecha de descarga

12. **Limpiar:**
    - Botón "LIMPIAR": Borra todos los campos del formulario
    - Botón "CANCELAR": Detiene la descarga en curso

---

## Tiempos de Descarga

### Mediciones en pruebas reales:

| Etapa | Tiempo promedio | Observación |
|-------|-----------------|-------------|
| **Autenticación** | 1-2 segundos | Constante |
| **Solicitud SAT** | < 1 segundo | Constante |
| **Procesamiento SAT** | 20-35 minutos | Variable según SAT |
| **Descarga por paquete** | 1-2 segundos | Constante |

### Log de ejemplo:
```
2026-03-19 13:54:27 - INICIANDO NUEVA DESCARGA
2026-03-19 13:54:28 - Token obtenido exitosamente
2026-03-19 13:54:29 - Solicitud aceptada
2026-03-19 13:54:29 - En proceso (SAT procesando)
...
2026-03-19 14:22:52 - Solicitud completada
2026-03-19 14:22:53 - Paquete descargado
TOTAL: ~28 minutos (depende del SAT)
```

### Factores que afectan el tiempo:
-  **Volumen de datos:** Mayor cantidad de CFDIs = más tiempo
-  **Ancho de banda:** Depende de tu conexión
-  **Horario:** El SAT puede estar más lento en horas pico
-  **Número de paquetes:** Cada paquete requiere descarga individual

---

##  Solución de Problemas

### Error: "No module named 'PyQt6'"
```bash
pip install PyQt6
```
*O al crear ejecutable:* `--hidden-import PyQt6`

### Error: "Exception: None"
- Verificar que los archivos `.cer` y `.key` sean válidos
- Revisar la conexión a Internet
- Consultar el archivo `cfdi_downloader.log`

### Error: "Error reading file 'autenticacion.xml'"
```bash
# Incluir toda la carpeta cfdiclient en el ejecutable
--add-data "ruta\a\cfdiclient;cfdiclient"
```

### Error: "No se permite la descarga de xml que se encuentren cancelados"
- Para Recibidos con CFDI, solo se pueden descargar vigentes
- Usar formato **Metadata** para incluir cancelados

### La descarga no inicia
- Verificar que el RFC tenga 12 o 13 caracteres
- Validar que las fechas no superen 1 año
- Confirmar que la FIEL esté vigente

### El icono no se ve en la barra de título
- Asegurar que el archivo `Img/Magistral.ico` existe
- En el ejecutable, verificar que se incluyó con `--add-data`

---
## Estructura del Proyecto

```
magistral-cfdi/
│
├── magistral_cfdi_v3.py
├── Img/
│   ├── Magistral.ico
│   ├── Descargar.png
│   ├── Cancelar.png
│   └── Limpiar.png
```

---

## Licencia

MIT License

Copyright (c) 2026 RAVEN DEVELOPERS BY GRUPO AISA

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 📧 Contacto

**Carlos Black**

- 📧 Email: taveramonroy04@gmail.com
-  Issues: [GitHub Issues](https://github.com/tuusuario/magistral-cfdi/issues)

---

## ¿Te ha sido útil?

Si este proyecto te ha sido de ayuda, no olvides darle una **estrella** en GitHub. ¡Gracias!

---

**¡Disfruta de Magistral CFDI 3.0.0!** 
