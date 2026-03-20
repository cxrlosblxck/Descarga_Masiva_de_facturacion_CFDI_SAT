
# CFDI_Manager 2.0.3 - Descarga Masiva de XML del SAT

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.3-red.svg)]()

**Desarrollado por Carlos Black**

---

## Tabla de Contenido
- [Descripción General](#descripción-general)
- [Características](#características)
- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Guía de Uso](#guía-de-uso)
- [Tiempos de Descarga](#tiempos-de-descarga)
- [Solución de Problemas](#solución-de-problemas)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Licencia](#licencia)
- [Contacto](#contacto)

---

## Descripción General

**CFDI_Manager 2.0.3** es una aplicación de escritorio desarrollada en Python con la librería Tkinter. Automatiza el proceso de autenticación, solicitud de descarga y verificación del estado de la solicitud de Comprobantes Fiscales Digitales por Internet (CFDI) desde el Servicio de Administración Tributaria (SAT) de México.

La aplicación permite descargar los CFDI **Emitidos** o **Recibidos** en un rango de fechas específico, con soporte para filtrado por estado y descarga paralela.

---

## Características

- Descarga de CFDIs **Emitidos** y **Recibidos**
- Soporte para **CFDI (XML)** y **Metadata (JSON)**
- Filtrado por estado: **Todos**, **Solo Vigentes**, **Solo Cancelados**
- Validación automática de **RFC** y **FIEL**
- Descarga **paralela** (3 hilos simultáneos)
- Sistema de **logging** (`cfdi_downloader.log`)
- Barra de progreso visual
- Registro de procesos en tiempo real
- Rango de fechas (máximo 1 año)
- Interfaz simple y funcional con Tkinter

---

## Requisitos del Sistema

### Software:
- Windows 10/11 (64 bits)
- Conexión estable a Internet

### Dependencias:
```txt
cfdiclient==1.6.2
tkcalendar==1.6.1
pyinstaller==6.11.1
```

---

## Instalación

### Ejecutable (Recomendado)
1. Descargar el ejecutable desde [Releases](https://github.com/cxrlos.black/cfdi-manager/releases)
2. Extraer el archivo `CFDI_Manager.zip`
3. Hacer doble clic en `CFDI_Manager.exe`

---

## Guía de Uso

### Pasos para descargar CFDIs:

1. **RFC del Contribuyente:** Ingresa tu Registro Federal de Contribuyentes (RFC).
2. **Archivos CER y KEY:** Selecciona los archivos `.cer` y `.key` de tu FIEL.
3. **Contraseña de la FIEL:** Ingresa la contraseña correspondiente.
4. **Carpeta de Descarga:** Selecciona la carpeta donde se guardarán los archivos ZIP.
5. **Tipo de Descarga:** Elige entre Emitidos o Recibidos.
6. **Estado CFDI:** Selecciona Todos, Solo Vigentes o Solo Cancelados.
7. **Rango de Fechas:** Ingresa las fechas en formato `YYYY-MM-DD` (máximo 1 año).
8. **Iniciar Descarga:** Haz clic en "Ejecutar Descarga".
9. **Registro de Procesos:** Observa el progreso y posibles errores en el área de texto.
10. **Limpiar:** Usa las opciones para limpiar log o campos del formulario.

---

## Tiempos de Descarga

| Etapa | Tiempo promedio | Observación |
|-------|-----------------|-------------|
| Autenticación | 1-2 segundos | Constante |
| Solicitud SAT | < 1 segundo | Constante |
| Procesamiento SAT | 20-35 minutos | Variable según SAT |
| Descarga por paquete | 1-2 segundos | Constante |

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

---

## Solución de Problemas

- **Error: "Exception: None"**  
  Verificar que los archivos `.cer` y `.key` sean válidos, revisar conexión a Internet, consultar `cfdi_downloader.log`.

- **Error: "Error reading file 'autenticacion.xml'"**  
  Incluir toda la carpeta `cfdiclient` en el ejecutable con `--add-data`.

- **Error: "No se permite la descarga de xml que se encuentren cancelados"**  
  Para Recibidos con CFDI, solo se pueden descargar vigentes. Usar formato Metadata para incluir cancelados.

- **La descarga no inicia**  
  Verificar RFC, fechas válidas y vigencia de la FIEL.

---

## Estructura del Proyecto

```
cfdi-manager/
│
├── CFDI_Manager2.0.3.py
├── icon.ico
```

---

## Licencia

MIT License

Copyright (c) Carlos Black
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

## Contacto

**Carlos Black**

- Email: taveramonroy04@gmail.com  
- Issues: [GitHub Issues](https://github.com/tuusuario/cfdi-manager/issues)

---

## ¿Te ha sido útil?

Si este proyecto te ha sido de ayuda, no olvides darle una **estrella** en GitHub. ¡Gracias!

---

**CFDI_Manager 2.0.3**
