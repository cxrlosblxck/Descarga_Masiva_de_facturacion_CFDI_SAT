# magistral_cfdi_v3.py
import sys
import os
import base64
import datetime
import time
import logging
import concurrent.futures
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QPixmap

# Importaciones de cfdiclient 
from cfdiclient import Autenticacion, DescargaMasiva, Fiel, VerificaSolicitudDescarga
from cfdiclient.solicitadescargaEmitidos import SolicitaDescargaEmitidos
from cfdiclient.solicitadescargaRecibidos import SolicitaDescargaRecibidos
# 
def resource_path(relative_path):
    """Obtener la ruta absoluta al recurso, funciona para dev y para PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

ESTADO_EMITIDOS = {
    "Todos":            None,   # SAT interpreta None como "todos"
    "Solo Vigentes":    1,
    "Solo Cancelados":  0,
}

ESTADO_RECIBIDOS_METADATA = {
    "Todos":            "Todos",
    "Solo Vigentes":    "Vigente",   # ← singular, con mayúscula
    "Solo Cancelados":  "Cancelado", # ← singular, con mayúscula
}

ESTADO_RECIBIDOS_CFDI = {
    # Con tipo_solicitud='CFDI' el SAT solo procesa vigentes
    "Todos":            "Vigente",
    "Solo Vigentes":    "Vigente",
    "Solo Cancelados":  "Vigente",   # Forzado; UI lo bloquea de todas formas
}


class DescargaWorker(QThread):
    """Worker para manejar la descarga en segundo plano"""
    progreso  = pyqtSignal(str)
    error     = pyqtSignal(str)
    finalizado = pyqtSignal(list)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.cancel_requested = False
        self.fiel = None
        self.auth = None
        self.descarga_masiva_instance = None
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            filename='cfdi_downloader.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("=" * 50)
        logging.info("INICIANDO NUEVA DESCARGA - MAGISTRAL CFDI 3.0.0")
        logging.info("=" * 50)

    def smart_polling_wait(self, attempt_count):
        if attempt_count <= 2:
            return 30
        elif attempt_count <= 5:
            return 45
        return 60

    def download_single_package(self, token, rfc, paquete, download_dir, package_number, total_packages):
        if self.cancel_requested:
            return None
        try:
            if not self.descarga_masiva_instance:
                self.descarga_masiva_instance = DescargaMasiva(self.fiel)

            descarga_paquete = self.descarga_masiva_instance.descargar_paquete(token, rfc, paquete)
            filename = os.path.join(download_dir, f'{paquete}.zip')

            with open(filename, 'wb') as fp:
                fp.write(base64.b64decode(descarga_paquete['paquete_b64']))

            mensaje = f" Paquete {package_number}/{total_packages} descargado: {paquete}.zip"
            self.progreso.emit(mensaje)
            logging.info(mensaje)

            return {
                'nombre': f'{paquete}.zip',
                'fecha':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ruta':   filename
            }
        except Exception as e:
            mensaje = f" Error descargando paquete {package_number}/{total_packages}: {str(e)}"
            self.progreso.emit(mensaje)
            logging.error(mensaje)
            return None

    def download_packages_parallel(self, token, rfc, paquetes, download_dir):
        resultados = []
        if not paquetes:
            self.progreso.emit("No hay paquetes para descargar")
            return resultados

        total_paquetes = len(paquetes)
        max_workers = 3
        self.progreso.emit(f" Iniciando descarga de {total_paquetes} paquetes...")
        logging.info(f"Iniciando descarga paralela de {total_paquetes} paquetes")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_paquete = {}
            for i, paquete in enumerate(paquetes, 1):
                future = executor.submit(
                    self.download_single_package,
                    token, rfc, paquete, download_dir, i, total_paquetes
                )
                future_to_paquete[future] = paquete

            for future in concurrent.futures.as_completed(future_to_paquete):
                if self.cancel_requested:
                    self.progreso.emit(" Cancelando descargas restantes...")
                    logging.info("Descarga cancelada por el usuario")
                    executor.shutdown(wait=False)
                    break
                try:
                    result = future.result()
                    if result:
                        resultados.append(result)
                except Exception as e:
                    self.progreso.emit(f" Error: {str(e)}")
                    logging.error(f"Error en descarga paralela: {str(e)}")

        return resultados

    def run(self):
        try:
            rfc              = self.config['rfc']
            cer_path         = self.config['cer']
            key_path         = self.config['key']
            password         = self.config['password']
            download_dir     = self.config['ubicacion']
            tipo_descarga    = self.config['tipo']        # 'Emitidos' | 'Recibidos'
            tipo_solicitud   = self.config['formato']     # 'CFDI' | 'Metadata'
            estado_comprobante = self.config['estado']    # valor ya mapeado correctamente
            fecha_inicial    = datetime.datetime.strptime(self.config['fecha_inicio'], '%Y-%m-%d').date()
            fecha_final      = datetime.datetime.strptime(self.config['fecha_fin'],    '%Y-%m-%d').date()

            logging.info(f"RFC: {rfc}")
            logging.info(f"Tipo: {tipo_descarga}")
            logging.info(f"Formato (tipo_solicitud): {tipo_solicitud}")
            logging.info(f"Estado comprobante enviado al SAT: {repr(estado_comprobante)}")
            logging.info(f"Fechas: {fecha_inicial} a {fecha_final}")
            logging.info(f"Directorio: {download_dir}")

            os.makedirs(download_dir, exist_ok=True)

            self.progreso.emit("Leyendo certificados...")
            cer_der = open(cer_path, 'rb').read()
            key_der = open(key_path, 'rb').read()
            self.fiel = Fiel(cer_der, key_der, password)

            self.auth = Autenticacion(self.fiel)
            self.auth.timeout = 60

            self.progreso.emit(" Obteniendo token...")
            token = self.auth.obtener_token()
            self.progreso.emit(" Token obtenido exitosamente")
            logging.info("Token obtenido correctamente")

            # ──────────────────────────────────────────────────────────────
            # SOLICITUD DE DESCARGA
            # ──────────────────────────────────────────────────────────────
            if tipo_descarga == "Emitidos":
                self.progreso.emit(f" Solicitando CFDIs Emitidos ({tipo_solicitud})...")
                logging.info("Solicitando CFDIs Emitidos")
                descarga = SolicitaDescargaEmitidos(self.fiel)
                solicitud = descarga.solicitar_descarga(
                    token,
                    rfc,
                    fecha_inicial,
                    fecha_final,
                    rfc_emisor=rfc,
                    tipo_solicitud=tipo_solicitud,          # 'CFDI'
                    estado_comprobante=estado_comprobante,  # None | 0 | 1
                )

            else:  # Recibidos
                self.progreso.emit(f" Solicitando CFDIs Recibidos ({tipo_solicitud})...")
                logging.info("Solicitando CFDIs Recibidos")
                descarga = SolicitaDescargaRecibidos(self.fiel)
                solicitud = descarga.solicitar_descarga(
                    token,
                    rfc,
                    fecha_inicial,
                    fecha_final,
                    rfc_receptor=rfc,
                    tipo_solicitud=tipo_solicitud,          # 'CFDI' o 'Metadata'
                    estado_comprobante=estado_comprobante,  # 'Vigente' | 'Cancelado' | 'Todos'
                )

            logging.info(f"Respuesta solicitud: {solicitud}")

            # Verificar que el SAT aceptó la solicitud
            cod = solicitud.get('cod_estatus', '')
            if cod != '5000':
                msg = solicitud.get('mensaje', f'Código de estatus inesperado: {cod}')
                self.error.emit(f"El SAT rechazó la solicitud: {msg}")
                logging.error(f"Solicitud rechazada: {solicitud}")
                return

            self.progreso.emit(f" Solicitud creada: {solicitud['id_solicitud']}")
            logging.info(f"Solicitud creada: {solicitud['id_solicitud']}")

            # ──────────────────────────────────────────────────────────────
            # CICLO DE VERIFICACIÓN
            # ──────────────────────────────────────────────────────────────
            attempt_count    = 0
            max_auth_retries = 3

            while not self.cancel_requested:
                try:
                    # Renovar token
                    token_retries = 0
                    while token_retries < max_auth_retries:
                        try:
                            token = self.auth.obtener_token()
                            self.progreso.emit(" Token renovado exitosamente")
                            break
                        except Exception as token_error:
                            token_retries += 1
                            if token_retries >= max_auth_retries:
                                raise
                            self.progreso.emit(f" Error renovando token (intento {token_retries}/{max_auth_retries})")
                            logging.warning(f"Error renovando token: {str(token_error)}")
                            time.sleep(10)

                    verificacion_obj = VerificaSolicitudDescarga(self.fiel)
                    verificacion     = verificacion_obj.verificar_descarga(token, rfc, solicitud['id_solicitud'])
                    estado_solicitud = int(verificacion['estado_solicitud'])

                    estados = {
                        1: " Aceptada",
                        2: " En proceso",
                        3: " Terminada",
                        4: " Error",
                        5: " Rechazada",
                        6: " Vencida"
                    }
                    estado_desc = estados.get(estado_solicitud, f" Estado {estado_solicitud}")
                    self.progreso.emit(f" Estado: {estado_desc}")
                    logging.info(f"Estado de solicitud: {estado_desc}")

                    if estado_solicitud <= 2:
                        wait_time = self.smart_polling_wait(attempt_count)
                        self.progreso.emit(f" Esperando {wait_time} segundos...")
                        for _ in range(wait_time):
                            if self.cancel_requested:
                                break
                            time.sleep(1)
                        attempt_count += 1
                        continue

                    elif estado_solicitud == 3:
                        self.progreso.emit(" Solicitud completada")
                        logging.info("Solicitud completada exitosamente")

                        if 'numero_cfdis' in verificacion:
                            self.progreso.emit(f" Documentos encontrados: {verificacion['numero_cfdis']}")

                        resultados = []
                        if verificacion.get('paquetes'):
                            self.progreso.emit(f" Paquetes disponibles: {len(verificacion['paquetes'])}")
                            resultados = self.download_packages_parallel(
                                token, rfc, verificacion['paquetes'], download_dir
                            )
                            self.progreso.emit("=" * 50)
                            self.progreso.emit(
                                f" TOTAL: {len(resultados)}/{len(verificacion['paquetes'])} paquetes descargados"
                            )
                            self.progreso.emit("=" * 50)
                            logging.info(f"Descarga completada: {len(resultados)} paquetes")
                        else:
                            self.progreso.emit("ℹ No se encontraron paquetes para descargar")
                            logging.info("No se encontraron paquetes para descargar")

                        self.finalizado.emit(resultados)
                        break

                    elif estado_solicitud >= 4:
                        error_msg = verificacion.get('mensaje', 'Error en la solicitud')
                        self.error.emit(f"Error: {estado_desc} - {error_msg}")
                        logging.error(f"Error en solicitud: {estado_desc} - {error_msg}")
                        break

                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower():
                        self.progreso.emit(f" Timeout en intento {attempt_count + 1}")
                        attempt_count += 1
                        if attempt_count < 5:
                            wait_time = min(30 * attempt_count, 90)
                            self.progreso.emit(f" Reintentando en {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            self.error.emit("Máximo de reintentos alcanzado")
                            break
                    else:
                        self.error.emit(f"Error: {error_msg}")
                        logging.error("Error durante verificación", exc_info=True)
                        break

        except Exception as e:
            self.error.emit(f"Error inesperado: {str(e)}")
            logging.error("Error inesperado", exc_info=True)

    def cancelar(self):
        self.cancel_requested = True
        logging.info("Cancelación solicitada por el usuario")


# ─────────────────────────────────────────────────────────────────────────────
# VENTANA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class MagistralCFDI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAGISTRAL CFDI 3.0.0")
        self.setMinimumSize(1300, 750)
        self.cargar_icono()
        self.worker = None
        self.cargar_imagenes()
        self.setup_ui()
        self.on_tipo_cambiado("Emitidos")

    def cargar_icono(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "Img", "Magistral.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f" No se pudo cargar el icono: {str(e)}")

    def cargar_imagenes(self):
        img_path = resource_path("Img")
        self.descargar_pixmap = QPixmap(os.path.join(img_path, "Descargar.png"))
        self.cancelar_pixmap  = QPixmap(os.path.join(img_path, "Cancelar.png"))
        self.limpiar_pixmap   = QPixmap(os.path.join(img_path, "Limpiar.png"))

        for px in [self.descargar_pixmap, self.cancelar_pixmap, self.limpiar_pixmap]:
            if px.isNull():
                print(" No se pudo cargar una imagen de botón")

        if not self.descargar_pixmap.isNull():
            self.descargar_pixmap = self.descargar_pixmap.scaled(
                140, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if not self.cancelar_pixmap.isNull():
            self.cancelar_pixmap = self.cancelar_pixmap.scaled(
                140, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if not self.limpiar_pixmap.isNull():
            self.limpiar_pixmap = self.limpiar_pixmap.scaled(
                140, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    # ──────────────────────────── UI ──────────────────────────────────────────

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vertical = QVBoxLayout(central_widget)
        main_vertical.setSpacing(15)
        main_vertical.setContentsMargins(20, 20, 20, 20)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        columns_layout.addWidget(self.crear_columna_izquierda())
        columns_layout.addWidget(self.crear_columna_derecha(), stretch=1)

        main_vertical.addLayout(columns_layout)
        self.crear_botones(main_vertical)

        desarrollador_label = QLabel("Carlos Black - MAGISTRAL CFDI 3.0.0")
        desarrollador_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desarrollador_label.setStyleSheet("""
            QLabel {
                color: #666; font-size: 11px;
                padding: 8px; border-top: 1px solid #ddd; margin-top: 5px;
            }
        """)
        main_vertical.addWidget(desarrollador_label)

    def crear_columna_izquierda(self):
        col = QWidget()
        col.setMaximumWidth(500)
        layout = QVBoxLayout(col)
        layout.setSpacing(12)

        # ── E.FIRMA ──────────────────────────────────────────────────────────
        firma_group = self.crear_grupo("ACCESO CON E.FIRMA", "#4CAF50")
        firma_layout = QGridLayout()
        firma_layout.setVerticalSpacing(8)
        firma_layout.setHorizontalSpacing(10)

        self._lbl_rfc = QLabel("RFC:")
        self._lbl_rfc.setStyleSheet("color: white;")
        firma_layout.addWidget(self._lbl_rfc, 0, 0)

        self.rfc_input = QLineEdit()
        self.rfc_input.setPlaceholderText("RFC del contribuyente")
        firma_layout.addWidget(self.rfc_input, 0, 1)

        label_password = self._lbl("CONTRASEÑA:")
        label_password.setStyleSheet("color: white;")
        firma_layout.addWidget(label_password, 1, 0)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        firma_layout.addWidget(self.password_input, 1, 1)

        label_cer = self._lbl("CERTIFICADO:")
        label_cer.setStyleSheet("color: white;")
        firma_layout.addWidget(label_cer, 2, 0)

        cer_layout = QHBoxLayout()
        self.cer_input = QLineEdit()
        self.cer_input.setPlaceholderText("Seleccionar .cer")
        self.cer_input.setReadOnly(True)
        self.cer_btn = QPushButton("📁")
        self.cer_btn.setFixedSize(30, 25)
        self.cer_btn.clicked.connect(lambda: self.browse_file(self.cer_input, "Certificados (*.cer)"))
        cer_layout.addWidget(self.cer_input)
        cer_layout.addWidget(self.cer_btn)
        firma_layout.addLayout(cer_layout, 2, 1)

        label_key = self._lbl("CLAVE PRIVADA:")
        label_key.setStyleSheet("color: white;")
        firma_layout.addWidget(label_key, 3, 0)

        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Seleccionar .key")
        self.key_input.setReadOnly(True)
        self.key_btn = QPushButton("📁")
        self.key_btn.setFixedSize(30, 25)
        self.key_btn.clicked.connect(lambda: self.browse_file(self.key_input, "Claves (*.key)"))
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.key_btn)
        firma_layout.addLayout(key_layout, 3, 1)

        firma_group.setLayout(firma_layout)
        layout.addWidget(firma_group)

        # ── INFORMACIÓN DE DESCARGA ───────────────────────────────────────────
        info_group = self.crear_grupo("INFORMACIÓN DE DESCARGA", "#2196F3")
        info_layout = QGridLayout()
        info_layout.setVerticalSpacing(8)
        info_layout.setHorizontalSpacing(10)

        label_tipo = self._lbl("TIPO:")
        label_tipo.setStyleSheet("color: white;")
        info_layout.addWidget(label_tipo, 0, 0)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["Emitidos", "Recibidos"])
        self.tipo_combo.currentTextChanged.connect(self.on_tipo_cambiado)
        info_layout.addWidget(self.tipo_combo, 0, 1)

        label_formato = self._lbl("FORMATO:")
        label_formato.setStyleSheet("color: white;")
        info_layout.addWidget(label_formato, 1, 0)
        self.formato_combo = QComboBox()
        self.formato_combo.addItems(["CFDI (XML)", "Metadata (JSON)"])
        self.formato_combo.currentTextChanged.connect(self.on_formato_cambiado)
        info_layout.addWidget(self.formato_combo, 1, 1)

        label_estado = self._lbl("ESTADO:")
        label_estado.setStyleSheet("color: white;")
        info_layout.addWidget(label_estado, 2, 0)

        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["Todos", "Solo Vigentes", "Solo Cancelados"])
        info_layout.addWidget(self.estado_combo, 2, 1)

        label_ubicacion = self._lbl("UBICACIÓN:")
        label_ubicacion.setStyleSheet("color: white;")
        info_layout.addWidget(label_ubicacion, 3, 0)

        ubicacion_layout = QHBoxLayout()
        self.ubicacion_input = QLineEdit()
        self.ubicacion_input.setPlaceholderText("Carpeta destino")
        self.ubicacion_input.setReadOnly(True)
        self.ubicacion_btn = QPushButton("📁")
        self.ubicacion_btn.setFixedSize(30, 25)
        self.ubicacion_btn.clicked.connect(self.browse_folder)
        ubicacion_layout.addWidget(self.ubicacion_input)
        ubicacion_layout.addWidget(self.ubicacion_btn)
        info_layout.addLayout(ubicacion_layout, 3, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # ── RANGO DE FECHAS ───────────────────────────────────────────────────
        fecha_group = self.crear_grupo("RANGO DE FECHAS", "#FF9800")
        fecha_layout = QHBoxLayout()
        fecha_layout.setSpacing(10)

        label_fecha_inicio = self._lbl("INICIO:")
        label_fecha_inicio.setStyleSheet("color: white;")
        fecha_layout.addWidget(label_fecha_inicio)

        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        fecha_layout.addWidget(self.fecha_inicio)

        label_fecha_final = self._lbl("FINAL:")
        label_fecha_final.setStyleSheet("color: white;")
        fecha_layout.addWidget(label_fecha_final)
        self.fecha_final = QDateEdit()
        self.fecha_final.setDate(QDate.currentDate())
        self.fecha_final.setCalendarPopup(True)
        self.fecha_final.setDisplayFormat("yyyy-MM-dd")
        fecha_layout.addWidget(self.fecha_final)

        fecha_group.setLayout(fecha_layout)
        layout.addWidget(fecha_group)

        layout.addStretch()
        return col

    def crear_columna_derecha(self):
        col = QWidget()
        right_layout = QVBoxLayout(col)
        right_layout.setSpacing(15)

        estado_group = self.crear_grupo("ESTADO DE DESCARGA", "#9C27B0")
        estado_layout = QVBoxLayout()
        estado_layout.setSpacing(15)

        self.mensaje_label = QLabel(" LISTO PARA COMENZAR")
        self.mensaje_label.setStyleSheet("""
            QLabel {
                background-color: white; color: black;
                padding: 25px; border-radius: 8px;
                font-weight: bold; border: 2px solid #9C27B0;
                font-size: 14px; min-height: 80px;
            }
        """)
        self.mensaje_label.setWordWrap(True)
        self.mensaje_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        estado_layout.addWidget(self.mensaje_label)

        self.tabla_resultados = QTableWidget()
        self.tabla_resultados.setColumnCount(2)
        self.tabla_resultados.setHorizontalHeaderLabels(["Archivo", "Fecha"])
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_resultados.setMinimumHeight(350)
        self.tabla_resultados.setVisible(False)
        estado_layout.addWidget(self.tabla_resultados)

        estado_group.setLayout(estado_layout)
        right_layout.addWidget(estado_group)
        return col

    def crear_botones(self, parent_layout):
        botones_widget = QWidget()
        botones_widget.setMaximumHeight(130)
        botones_layout = QHBoxLayout(botones_widget)
        botones_layout.setSpacing(40)
        botones_layout.setContentsMargins(20, 10, 20, 10)
        botones_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def make_btn_block(pixmap, label_text, color, hover_color, on_click, enabled=True):
            container = QVBoxLayout()
            container.setSpacing(5)
            container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if not pixmap.isNull():
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setFixedSize(140, 45)
                container.addWidget(img_label)
            btn = QPushButton(label_text)
            btn.setMinimumSize(140, 35)
            btn.setEnabled(enabled)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}; color: white;
                    font-weight: bold; border: none;
                    border-radius: 5px; font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {hover_color}; }}
                QPushButton:disabled {{ background-color: #cccccc; }}
            """)
            btn.clicked.connect(on_click)
            container.addWidget(btn)
            return container, btn

        d_cont, self.descargar_btn = make_btn_block(
            self.descargar_pixmap, "DESCARGAR", "#4CAF50", "#45a049", self.iniciar_descarga)
        c_cont, self.cancelar_btn  = make_btn_block(
            self.cancelar_pixmap,  "CANCELAR",  "#f44336", "#d32f2f", self.cancelar_descarga, enabled=False)
        l_cont, self.limpiar_btn   = make_btn_block(
            self.limpiar_pixmap,   "LIMPIAR",   "#2196F3", "#1976D2", self.limpiar_campos)

        botones_layout.addLayout(d_cont)
        botones_layout.addLayout(c_cont)
        botones_layout.addLayout(l_cont)
        parent_layout.addWidget(botones_widget)

    # ──────────────────────────── Helpers UI ─────────────────────────────────

    def crear_grupo(self, titulo, color):
        group = QGroupBox(titulo)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold; border: 2px solid {color};
                border-radius: 5px; margin-top: 10px;
                padding-top: 10px; font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 10px;
                padding: 0 5px 0 5px; color: {color};
            }}
        """)
        return group

    def _lbl(self, texto):
        """Label con estilo blanco-negrita para encabezados de formulario"""
        label = QLabel(texto)
        label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        return label

    # ──────────────────────────── Lógica de combos ───────────────────────────

    def on_tipo_cambiado(self, tipo):
        """Ajusta el combo de estado y el mensaje según el tipo seleccionado"""
        self._actualizar_restricciones(tipo, self.formato_combo.currentText())

    def on_formato_cambiado(self, formato):
        """Ajusta el combo de estado y el mensaje según el formato seleccionado"""
        self._actualizar_restricciones(self.tipo_combo.currentText(), formato)

    def _actualizar_restricciones(self, tipo, formato):
        """
        Reglas del SAT:
          Emitidos  + CFDI     → Todos / Vigentes / Cancelados  (OK)
          Recibidos + CFDI     → Solo Vigentes (SAT no acepta cancelados con CFDI)
          Recibidos + Metadata → Todos / Vigentes / Cancelados  (OK)
        """
        cfdi_format = formato.startswith("CFDI")

        if tipo == "Emitidos":
            self.estado_combo.setEnabled(True)
            # Restaurar opciones completas si fueron limitadas
            if self.estado_combo.count() != 3:
                self.estado_combo.clear()
                self.estado_combo.addItems(["Todos", "Solo Vigentes", "Solo Cancelados"])
            self.mensaje_label.setText(" EMITIDOS: TODOS LOS ESTADOS DISPONIBLES")

        else:  # Recibidos
            if cfdi_format:
                # Recibidos + CFDI → solo vigentes
                self.estado_combo.setCurrentText("Solo Vigentes")
                self.estado_combo.setEnabled(False)
                self.mensaje_label.setText(
                    " RECIBIDOS + CFDI (XML) = SOLO VIGENTES\n"
                    "Para cancelados usa Metadata (JSON)"
                )
            else:
                # Recibidos + Metadata → todos los estados
                self.estado_combo.setEnabled(True)
                self.mensaje_label.setText(
                    " RECIBIDOS + METADATA = TODOS LOS ESTADOS\n"
                    "(Vigentes, Cancelados o Todos)"
                )

    # ──────────────────────────── Mapeo de estado ────────────────────────────

    def get_estado_comprobante(self):
        """
        Devuelve el valor EXACTO que espera la API del SAT para estado_comprobante.

        Emitidos  → None | 0 | 1   (entero o None)
        Recibidos → 'Todos' | 'Vigente' | 'Cancelado'  (string singular)
        """
        tipo_descarga  = self.tipo_combo.currentText()
        estado_texto   = self.estado_combo.currentText()
        formato        = self.formato_combo.currentText()

        if tipo_descarga == "Emitidos":
            return ESTADO_EMITIDOS.get(estado_texto)

        else:  # Recibidos
            if formato.startswith("CFDI"):
                return ESTADO_RECIBIDOS_CFDI.get(estado_texto, "Vigente")
            else:
                return ESTADO_RECIBIDOS_METADATA.get(estado_texto, "Todos")

    def get_tipo_solicitud(self):
        """Devuelve 'CFDI' o 'Metadata' según el combo de formato"""
        return 'CFDI' if self.formato_combo.currentText().startswith("CFDI") else 'Metadata'

    # ──────────────────────────── Archivos / carpetas ────────────────────────

    def browse_file(self, line_edit, filtro):
        filename, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", filtro)
        if filename:
            line_edit.setText(os.path.basename(filename))
            line_edit.setProperty("ruta_completa", filename)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de descarga")
        if folder:
            self.ubicacion_input.setText(os.path.basename(folder))
            self.ubicacion_input.setProperty("ruta_completa", folder)

    def obtener_ruta_completa(self, widget, default=""):
        ruta = widget.property("ruta_completa")
        return ruta if ruta else default

    # ──────────────────────────── Validación ─────────────────────────────────

    def validar_campos(self):
        if not self.rfc_input.text():
            QMessageBox.warning(self, "Error", "RFC es obligatorio")
            return False
        if not self.password_input.text():
            QMessageBox.warning(self, "Error", "Contraseña es obligatoria")
            return False
        if not self.obtener_ruta_completa(self.cer_input):
            QMessageBox.warning(self, "Error", "Debe seleccionar un archivo CER")
            return False
        if not self.obtener_ruta_completa(self.key_input):
            QMessageBox.warning(self, "Error", "Debe seleccionar un archivo KEY")
            return False
        rfc = self.rfc_input.text().strip()
        if len(rfc) not in (12, 13):
            QMessageBox.warning(self, "Error", "RFC debe tener 12 o 13 caracteres")
            return False
        fecha_inicio = self.fecha_inicio.date().toPyDate()
        fecha_fin    = self.fecha_final.date().toPyDate()
        if fecha_fin < fecha_inicio:
            QMessageBox.warning(self, "Error", "La fecha final no puede ser menor que la inicial")
            return False
        if (fecha_fin - fecha_inicio).days > 365:
            QMessageBox.warning(self, "Error", "El rango de fechas no puede ser mayor a 1 año")
            return False
        return True

    # ──────────────────────────── Acciones ───────────────────────────────────

    def iniciar_descarga(self):
        if not self.validar_campos():
            return

        self.descargar_btn.setEnabled(False)
        self.cancelar_btn.setEnabled(True)
        self.limpiar_btn.setEnabled(False)
        self.mensaje_label.setText(" INICIANDO DESCARGA...")
        self.tabla_resultados.setVisible(False)
        self.tabla_resultados.setRowCount(0)

        estado_valor   = self.get_estado_comprobante()
        tipo_solicitud = self.get_tipo_solicitud()

        config = {
            'rfc':          self.rfc_input.text().strip().upper(),
            'password':     self.password_input.text(),
            'cer':          self.obtener_ruta_completa(self.cer_input),
            'key':          self.obtener_ruta_completa(self.key_input),
            'tipo':         self.tipo_combo.currentText(),    # 'Emitidos' | 'Recibidos'
            'formato':      tipo_solicitud,                   # 'CFDI' | 'Metadata'
            'estado':       estado_valor,                     # valor correcto para la API
            'ubicacion':    self.obtener_ruta_completa(self.ubicacion_input, os.getcwd()),
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin':    self.fecha_final.date().toString("yyyy-MM-dd"),
        }

        print(f" Configuración enviada al SAT:")
        print(f"  - Tipo:    {config['tipo']}")
        print(f"  - Formato: {config['formato']}")
        print(f"  - Estado:  {repr(config['estado'])}")

        self.worker = DescargaWorker(config)
        self.worker.progreso.connect(self.actualizar_mensaje)
        self.worker.error.connect(self.mostrar_error)
        self.worker.finalizado.connect(self.mostrar_resultados)
        self.worker.start()

    def actualizar_mensaje(self, mensaje):
        self.mensaje_label.setText(mensaje)

    def mostrar_resultados(self, archivos):
        self.tabla_resultados.setVisible(True)
        self.tabla_resultados.setRowCount(len(archivos))
        for i, archivo in enumerate(archivos):
            self.tabla_resultados.setItem(i, 0, QTableWidgetItem(archivo['nombre']))
            self.tabla_resultados.setItem(i, 1, QTableWidgetItem(archivo['fecha']))
        self.descargar_btn.setEnabled(True)
        self.cancelar_btn.setEnabled(False)
        self.limpiar_btn.setEnabled(True)
        self.mensaje_label.setText(f" DESCARGA COMPLETADA: {len(archivos)} ARCHIVO(S)")

    def mostrar_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        self.mensaje_label.setText(f" ERROR: {error_msg}")
        self.descargar_btn.setEnabled(True)
        self.cancelar_btn.setEnabled(False)
        self.limpiar_btn.setEnabled(True)

        # Sugerir cambio a Metadata si el error parece ser de estado
        if (self.tipo_combo.currentText() == "Recibidos"
                and self.formato_combo.currentText().startswith("CFDI")
                and "cancelado" in error_msg.lower()):
            reply = QMessageBox.question(
                self, "Sugerencia",
                "¿Quieres cambiar a Metadata para incluir CFDIs cancelados?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.formato_combo.setCurrentText("Metadata (JSON)")

    def cancelar_descarga(self):
        if self.worker:
            self.worker.cancelar()
            self.mensaje_label.setText(" CANCELANDO DESCARGA...")
            self.descargar_btn.setEnabled(True)
            self.cancelar_btn.setEnabled(False)
            self.limpiar_btn.setEnabled(True)

    def limpiar_campos(self):
        self.rfc_input.clear()
        self.password_input.clear()
        self.cer_input.clear()
        self.key_input.clear()
        self.ubicacion_input.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.formato_combo.setCurrentIndex(0)
        self.estado_combo.setCurrentIndex(0)
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_final.setDate(QDate.currentDate())
        self.tabla_resultados.setVisible(False)
        self.mensaje_label.setText(" CAMPOS LIMPIADOS")
        for widget in [self.cer_input, self.key_input, self.ubicacion_input]:
            widget.setProperty("ruta_completa", None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MagistralCFDI()
    window.show()
    sys.exit(app.exec())
