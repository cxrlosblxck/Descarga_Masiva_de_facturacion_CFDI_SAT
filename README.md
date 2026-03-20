## Magistral CFDI - Descarga Masiva de XML del SAT

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.0.0-red.svg)]()

**Desarrollado por Carlos Black**

---

## Tabla de Contenido:
- [Descripción General](#descripción-general)
- [Versiones Disponibles](#versiones-disponibles)
- [Guía para Contribuidores](#guía-para-contribuidores)
- [Licencia](#licencia)
- [Contacto](#contacto)

---

## Descripción General

La aplicación **Magistral CFDI** automatiza el proceso de autenticación, solicitud de descarga y verificación del estado de la solicitud de Comprobantes Fiscales Digitales por Internet (CFDI) desde el Servicio de Administración Tributaria (SAT) de México.

La suite cuenta con **dos versiones funcionales** que se mantienen activas para diferentes necesidades:

| Versión | Framework | Descripción |
|---------|-----------|-------------|
| **CFDI_Manager 2.0.3** | tkinter | Versión clásica, ligera y funcional |
| **Magistral CFDI 3.0.0** | PyQt6 | Versión moderna con interfaz visual mejorada |

---

## Versiones Disponibles

### CFDI_Manager 2.0.3 (Clásica)
-  Interfaz funcional basada en tkinter
-  Ligera y rápida (~15 MB)
-  Ideal para equipos con recursos limitados
-  Mantenimiento activo

### Magistral CFDI 3.0.0 (Moderna)
-  Interfaz moderna con PyQt6
-  Imágenes personalizadas
-  Tabla de resultados visual
-  Tooltips informativos
-  Actualización en tiempo real

---

## Características

### Ambas versiones:
-  Descarga de CFDIs **Emitidos** y **Recibidos**
-  Soporte para **CFDI (XML)** y **Metadata (JSON)**
-  Filtrado por estado: **Todos**, **Solo Vigentes**, **Solo Cancelados**
-  Validación automática de **RFC** y **FIEL**
-  Descarga **paralela** (3 hilos simultáneos)
-  Sistema de **logging** (`cfdi_downloader.log`)
-  Manejo de errores con sugerencias inteligentes
-  Rango de fechas (máximo 1 año)

### Solo Magistral CFDI 3.0.0:
-  Tema visual Fusion
-  Imágenes en botones (Descargar, Cancelar, Limpiar)
-  Tabla interactiva de resultados
-  Barra de progreso visual
-  Tooltips informativos en cada campo

---

## Requisitos del Sistema

### Software:
- Windows 10/11 (64 bits)
- Python 3.8 o superior (para desarrollo)
- Conexión estable a Internet
---
### Dependencias:
```txt
# Para CFDI_Manager 2.0.3
cfdiclient==1.6.2
tkcalendar==1.6.1
pyinstaller==6.11.1

# Para Magistral CFDI 3.0.0
PyQt6==6.9.1
cfdiclient==1.6.2
pyinstaller==6.11.1
```
---
## Guía para Contribuidores:
¡Gracias por tu interés en contribuir! Tu ayuda es valiosa para mejorar esta herramienta.

¿Cómo puedo contribuir?
Reportar errores (Bugs)
Utiliza el sistema de seguimiento de errores (Issues) de GitHub

## Proporciona:

Título del error: Descriptivo y conciso

Descripción detallada: Explica el problema claramente

Pasos para reproducir: Lista los pasos necesarios

Comportamiento esperado vs. real: Describe qué debería pasar

Información del entorno: Sistema operativo, versión de Python, dependencias

Capturas de pantalla: Si son útiles

Sugerir mejoras (Features)
Utiliza el sistema de seguimiento de errores (Issues)

Describe claramente la mejora propuesta y su justificación

Contribuir con código
Fork del repositorio en GitHub

## Desarrollo del código:

Sigue PEP 8 (usa flake8 o pylint)

Documenta tu código usando docstrings

Escribe pruebas unitarias (unittest o pytest)

Commit de los cambios: Mensajes claros y concisos

Push de la rama a tu repositorio fork

Creación de un Pull Request (PR)

Revisión del código por los mantenedores

Merge del PR al repositorio principal

Contribuir con documentación
Si encuentras errores o quieres agregar información, envía un PR con los cambios

##  Licencia
MIT License

Copyright (c) 2026 RAVEN DEVELOPERS BY GRUPO AISA

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.

## Contacto

📧 Email: taveramonroy04@gmail.com

🐛 Issues: GitHub Issues

¿Te ha sido útil?
Si este proyecto te ha sido de ayuda, no olvides darle una estrella en GitHub. ¡Gracias!

¡Disfruta de Magistral CFDI!
