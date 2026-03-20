# -*- coding: utf-8 -*-
#Carlos Black - Versión Mejorada para CFDIs Vigentes y Cancelados
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import base64
import datetime
import os
import time
import threading
import logging
import concurrent.futures
from tkcalendar import DateEntry
from cfdiclient import Autenticacion, DescargaMasiva, Fiel, VerificaSolicitudDescarga
from cfdiclient.solicitadescargaEmitidos import SolicitaDescargaEmitidos
from cfdiclient.solicitadescargaRecibidos import SolicitaDescargaRecibidos

class CFDIDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CFDI Manager - Descarga Vigentes y Cancelados")
        self.root.geometry("950x750")
        
        # Variables de control
        self.is_downloading = False
        self.cancel_requested = False
        self.current_thread = None
        
        # Variables para reutilizar instancias
        self.fiel = None
        self.auth = None
        self.descarga_masiva_instance = None
        
        # Configurar logging
        self.setup_logging()
        
        # Crear marco principal
        self.setup_ui()

    def setup_logging(self):
        """Configura el sistema de logging"""
        logging.basicConfig(
            filename='cfdi_downloader.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_ui(self):
        """Configura la interfaz de usuario mejorada"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(3, weight=1)

        # Columna izquierda para campos de entrada
        input_column_frame = ttk.Frame(main_frame)
        input_column_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # RFC con validación
        ttk.Label(input_column_frame, text="RFC:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.rfc_entry = ttk.Entry(input_column_frame, width=35)
        self.rfc_entry.grid(row=0, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        self.rfc_entry.bind("<FocusOut>", self.validate_rfc)

        # Archivo CER
        ttk.Label(input_column_frame, text="Archivo CER (.cer):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.cer_entry = ttk.Entry(input_column_frame, width=35)
        self.cer_entry.grid(row=1, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(input_column_frame, text="Examinar", width=10, command=self.browse_cer).grid(row=1, column=2, padx=5, pady=2)

        # Archivo KEY
        ttk.Label(input_column_frame, text="Archivo KEY (.key):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.key_entry = ttk.Entry(input_column_frame, width=35)
        self.key_entry.grid(row=2, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(input_column_frame, text="Examinar", width=10, command=self.browse_key).grid(row=2, column=2, padx=5, pady=2)

        # Contraseña
        ttk.Label(input_column_frame, text="Contraseña:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.password_entry = ttk.Entry(input_column_frame, width=35, show="*")
        self.password_entry.grid(row=3, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))

        # Carpeta de Descarga
        ttk.Label(input_column_frame, text="Carpeta de Descarga:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.download_dir_entry = ttk.Entry(input_column_frame, width=35)
        self.download_dir_entry.grid(row=4, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(input_column_frame, text="Examinar", width=10, command=self.browse_download_dir).grid(row=4, column=2, padx=5, pady=2)

        # Tipo de Descarga
        ttk.Label(input_column_frame, text="Tipo de Descarga:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.download_type_combobox = ttk.Combobox(input_column_frame, width=32, state="readonly")
        self.download_type_combobox['values'] = ("Emitidos", "Recibidos")
        self.download_type_combobox.grid(row=5, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        self.download_type_combobox.current(0)
        # Vincular evento de cambio
        self.download_type_combobox.bind('<<ComboboxSelected>>', self.on_download_type_change)

        # Estado de Comprobante
        ttk.Label(input_column_frame, text="Estado CFDI:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.cfdi_status_combobox = ttk.Combobox(input_column_frame, width=32, state="readonly")
        self.cfdi_status_combobox['values'] = ("Todos", "Solo Vigentes", "Solo Cancelados")
        self.cfdi_status_combobox.grid(row=6, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
        self.cfdi_status_combobox.current(0)
        
        # Etiqueta de información dinámica
        self.status_info_label = ttk.Label(input_column_frame, text="", foreground="blue")
        self.status_info_label.grid(row=6, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Etiqueta de formato
        self.format_info_label = ttk.Label(input_column_frame, text="", foreground="purple")
        self.format_info_label.grid(row=7, column=1, sticky=tk.W, padx=5, pady=2)

        # Variables internas fijas
        self.parallel_threads_var = tk.IntVar(value=3)
        self.parallel_download_var = tk.BooleanVar(value=True)
        self.smart_polling_var = tk.BooleanVar(value=True)

        # Marco de Fechas con Calendario
        date_frame = ttk.LabelFrame(main_frame, text="Establezca un rango de fechas para la descarga", padding="5")
        date_frame.grid(row=0, column=3, rowspan=2, padx=20, sticky=(tk.N, tk.S, tk.E, tk.W))
        date_frame.columnconfigure(0, weight=1)

        ttk.Label(date_frame, text="Fecha Inicial").grid(row=0, column=0, pady=2, sticky=tk.W)
        self.start_date_entry = DateEntry(date_frame, width=20, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=1, column=0, pady=2, padx=5, sticky=tk.W)

        ttk.Label(date_frame, text="Fecha Final").grid(row=2, column=0, pady=2, sticky=tk.W)
        self.end_date_entry = DateEntry(date_frame, width=20, date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=3, column=0, pady=2, padx=5, sticky=tk.W)

        # Botón para establecer fechas del último mes
        ttk.Button(date_frame, text="Último Mes", command=self.set_last_month_dates).grid(row=4, column=0, pady=5, sticky=tk.W)

        # Área de Procesos
        ttk.Label(main_frame, text="Registro de Procesos:").grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.process_text = scrolledtext.ScrolledText(main_frame, width=70, height=15, state='disabled')
        self.process_text.grid(row=9, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.grid(row=10, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))

        # Botones principales
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=3, pady=10, sticky=tk.E)
        
        self.download_btn = ttk.Button(button_frame, text="Ejecutar Descarga", command=self.start_download)
        self.download_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancelar", command=self.cancel_download, state='disabled')
        self.cancel_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Limpiar Log", command=self.clear_log)
        self.clear_btn.grid(row=1, column=0, padx=5, pady=5)
        
        self.clear_fields_btn = ttk.Button(button_frame, text="Limpiar Campos", command=self.clear_fields)
        self.clear_fields_btn.grid(row=1, column=1, padx=5, pady=5)

        # Etiqueta del desarrollador
        ttk.Label(main_frame, text="Carlos Black - Versión 2.0.3").grid(row=11, column=0, columnspan=5, pady=10, sticky=tk.W)

        # Inicializar estado de la interfaz
        self.on_download_type_change()

    def on_download_type_change(self, event=None):
        """Actualiza la interfaz cuando cambia el tipo de descarga"""
        tipo = self.download_type_combobox.get()
        
        if tipo == "Recibidos":
            # Para Recibidos: Metadata permite todos los estados
            self.cfdi_status_combobox.configure(state='readonly')
            self.cfdi_status_combobox.set("Todos")
            self.status_info_label.config(
                text=" Recibidos: Todos los estados", 
                foreground="green"
            )
            self.format_info_label.config(
                text=" Formato: METADATA (contiene UUID, RFC, fechas)", 
                foreground="blue"
            )
        else:  # Emitidos
            # Para Emitidos: CFDI permite filtrar por estado
            self.cfdi_status_combobox.configure(state='readonly')
            self.cfdi_status_combobox.set("Todos")
            self.status_info_label.config(
                text=" Emitidos: Todos los estados", 
                foreground="green"
            )
            self.format_info_label.config(
                text=" Formato: CFDI (XML completos)", 
                foreground="blue"
            )

    def get_estado_comprobante(self):
        """Obtiene el estado del comprobante según selección del usuario"""
        tipo_descarga = self.download_type_combobox.get()
        estado_texto = self.cfdi_status_combobox.get()
        
        if tipo_descarga == "Emitidos":
            # Para Emitidos: 0=cancelados, 1=vigentes, None=todos
            mapping = {
                "Todos": None,
                "Solo Vigentes": 1,
                "Solo Cancelados": 0
            }
            return mapping.get(estado_texto)
        else:
            # Para Recibidos: strings 'Todos', 'Vigentes', 'Cancelados'
            mapping = {
                "Todos": "Todos",
                "Solo Vigentes": "Vigentes",
                "Solo Cancelados": "Cancelados"
            }
            return mapping.get(estado_texto, "Todos")

    def get_tipo_solicitud(self):
        """Determina el tipo de solicitud según el tipo de descarga"""
        tipo_descarga = self.download_type_combobox.get()
        if tipo_descarga == "Recibidos":
            return 'Metadata'  # Recibidos usa Metadata
        else:
            return 'CFDI'  # Emitidos usa CFDI

    def set_last_month_dates(self):
        """Establece fechas del último mes"""
        today = datetime.date.today()
        last_month = today.replace(day=1) - datetime.timedelta(days=1)
        first_day_last_month = last_month.replace(day=1)
        
        self.start_date_entry.set_date(first_day_last_month)
        self.end_date_entry.set_date(last_month)
        self.log_process(f"Fechas establecidas: {first_day_last_month} a {last_month}")

    def smart_polling_wait(self, attempt_count):
        """Implementa espera adaptiva basada en intentos"""
        if attempt_count <= 2:
            return 30
        elif attempt_count <= 5:
            return 45
        else:
            return 60

    def cancel_download(self):
        """Cancela la descarga en progreso"""
        self.cancel_requested = True
        self.log_process(" Cancelación solicitada. Esperando finalización del proceso actual...")
        self.cancel_btn.configure(state='disabled')

    def download_single_package(self, token, rfc, paquete, download_dir, package_number, total_packages):
        """Descarga un paquete individual"""
        if self.cancel_requested:
            return f" Cancelado: {paquete}"
            
        try:
            if not self.descarga_masiva_instance:
                self.descarga_masiva_instance = DescargaMasiva(self.fiel)
                
            descarga_paquete = self.descarga_masiva_instance.descargar_paquete(token, rfc, paquete)
            
            # Determinar extensión según el tipo de contenido
            tipo_descarga = self.download_type_combobox.get()
            if tipo_descarga == "Recibidos":
                # Para Metadata, puede ser .zip con archivos JSON
                filename = os.path.join(download_dir, f'{paquete}.zip')
            else:
                # Para CFDI, siempre .zip con XML
                filename = os.path.join(download_dir, f'{paquete}.zip')
            
            with open(filename, 'wb') as fp:
                fp.write(base64.b64decode(descarga_paquete['paquete_b64']))
            
            return f" Paquete {package_number}/{total_packages} descargado: {os.path.basename(filename)}"
            
        except Exception as e:
            return f" Error descargando paquete {package_number}/{total_packages} ({paquete}): {str(e)}"

    def download_packages_parallel(self, token, rfc, paquetes, download_dir):
        """Descarga paquetes en paralelo"""
        if not paquetes:
            self.log_process("No hay paquetes para descargar")
            return
            
        total_paquetes = len(paquetes)
        max_workers = self.parallel_threads_var.get()
        
        self.log_process(f" Iniciando descarga paralela de {total_paquetes} paquetes con {max_workers} hilo(s)...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_info = {}
            for i, paquete in enumerate(paquetes, 1):
                future = executor.submit(
                    self.download_single_package, 
                    token, rfc, paquete, download_dir, i, total_paquetes
                )
                future_to_info[future] = {'paquete': paquete, 'numero': i}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_info):
                if self.cancel_requested:
                    self.log_process(" Cancelando descargas restantes...")
                    executor.shutdown(wait=False)
                    break
                    
                info = future_to_info[future]
                try:
                    result = future.result()
                    self.log_process(result)
                    completed += 1
                    
                    # Actualizar progreso
                    progress = 70 + (completed / total_paquetes) * 30
                    self.progress_bar["value"] = progress
                    self.root.update_idletasks()
                    
                except Exception as e:
                    self.log_process(f" Error en paquete {info['numero']}: {str(e)}")

    def validate_download_completeness(self, expected_packages, download_dir):
        """Valida que todos los paquetes se descargaron correctamente"""
        self.log_process(" Validando completitud de descarga...")
        
        downloaded_files = []
        missing_files = []
        corrupted_files = []
        
        for paquete in expected_packages:
            filename = os.path.join(download_dir, f'{paquete}.zip')
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                if file_size > 0:
                    downloaded_files.append(paquete)
                    self.log_process(f" {paquete}.zip - OK ({file_size:,} bytes)")
                else:
                    corrupted_files.append(paquete)
                    self.log_process(f" {paquete}.zip - CORRUPTO (0 bytes)")
            else:
                missing_files.append(paquete)
                self.log_process(f" {paquete}.zip - FALTANTE")
        
        # Resumen final
        total_expected = len(expected_packages)
        total_downloaded = len(downloaded_files)
        
        self.log_process("=" * 50)
        self.log_process(f" RESUMEN: {total_downloaded}/{total_expected} paquetes descargados")
        self.log_process("=" * 50)
        
        if missing_files or corrupted_files:
            failed_packages = missing_files + corrupted_files
            response = messagebox.askyesno(
                "Descarga Incompleta", 
                f"Se encontraron {len(failed_packages)} paquete(s) con problemas.\n"
                f"¿Desea reintentar la descarga?"
            )
            
            if response:
                return failed_packages
        
        return []

    def validate_rfc(self, event=None):
        """Valida que el RFC tenga un formato básicamente correcto"""
        rfc = self.rfc_entry.get().strip()
        if len(rfc) not in (12, 13):
            messagebox.showwarning("RFC Inválido", "El RFC debe tener 12 o 13 caracteres")
            return False
        return True

    def browse_cer(self):
        filename = filedialog.askopenfilename(filetypes=[("Archivos CER", "*.cer")])
        if filename:
            self.cer_entry.delete(0, tk.END)
            self.cer_entry.insert(0, filename)

    def browse_key(self):
        filename = filedialog.askopenfilename(filetypes=[("Archivos KEY", "*.key")])
        if filename:
            self.key_entry.delete(0, tk.END)
            self.key_entry.insert(0, filename)

    def browse_download_dir(self):
        directory = filedialog.askdirectory(title="Seleccionar Carpeta de Descarga")
        if directory:
            self.download_dir_entry.delete(0, tk.END)
            self.download_dir_entry.insert(0, directory)

    def clear_log(self):
        self.process_text.configure(state='normal')
        self.process_text.delete(1.0, tk.END)
        self.process_text.configure(state='disabled')

    def log_process(self, message):
        self.process_text.configure(state='normal')
        self.process_text.insert(tk.END, f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        self.process_text.see(tk.END)
        self.process_text.configure(state='disabled')
        logging.info(message)

    def validate_inputs(self):
        required_fields = {
            'RFC': self.rfc_entry.get(),
            'Archivo CER': self.cer_entry.get(),
            'Archivo KEY': self.key_entry.get(),
            'Contraseña': self.password_entry.get(),
            'Fecha Inicial': self.start_date_entry.get(),
            'Fecha Final': self.end_date_entry.get()
        }
        
        for field, value in required_fields.items():
            if not value.strip():
                messagebox.showerror("Error", f"El campo {field} es obligatorio")
                return False
        
        if not self.validate_rfc():
            return False
            
        try:
            fecha_inicial = datetime.datetime.strptime(self.start_date_entry.get(), '%Y-%m-%d')
            fecha_final = datetime.datetime.strptime(self.end_date_entry.get(), '%Y-%m-%d')
            
            if fecha_final < fecha_inicial:
                messagebox.showerror("Error", "La fecha final no puede ser menor que la fecha inicial")
                return False
                
            if (fecha_final - fecha_inicial).days > 365:
                messagebox.showerror("Error", "El rango de fechas no puede ser mayor a 1 año")
                return False
                
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD")
            return False
            
        if not os.path.exists(self.cer_entry.get()):
            messagebox.showerror("Error", f"El archivo {self.cer_entry.get()} no existe")
            return False
            
        if not os.path.exists(self.key_entry.get()):
            messagebox.showerror("Error", f"El archivo {self.key_entry.get()} no existe")
            return False
            
        return True

    def validate_fiel_files(self):
        """Valida que los archivos CER y KEY sean válidos"""
        try:
            cer_der = open(self.cer_entry.get(), 'rb').read()
            key_der = open(self.key_entry.get(), 'rb').read()
            password = self.password_entry.get()
            
            test_fiel = Fiel(cer_der, key_der, password)
            self.log_process(" Archivos FIEL validados correctamente")
            return True
        except Exception as e:
            self.log_process(f" Error validando FIEL: {str(e)}")
            messagebox.showerror("Error FIEL", f"Los archivos FIEL no son válidos: {str(e)}")
            return False

    def start_download(self):
        if self.is_downloading:
            self.log_process("Ya hay una descarga en proceso")
            return
            
        if not self.validate_inputs():
            return
            
        if not self.validate_fiel_files():
            return
            
        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.progress_bar["value"] = 0
        
        # Mostrar configuración seleccionada
        tipo_descarga = self.download_type_combobox.get()
        estado_seleccionado = self.cfdi_status_combobox.get()
        tipo_solicitud = self.get_tipo_solicitud()
        self.log_process(f" Configuración: {tipo_descarga} - {estado_seleccionado} ({tipo_solicitud})")
        
        threading.Thread(target=self.download_process, daemon=True).start()

    def download_process(self):
        """Versión con Emitidos=CFDI y Recibidos=Metadata"""
        try:
            rfc = self.rfc_entry.get().strip()
            cer_path = self.cer_entry.get()
            key_path = self.key_entry.get()
            password = self.password_entry.get()
            download_dir = self.download_dir_entry.get()
            
            if not download_dir:
                download_dir = os.getcwd()
                self.log_process("Usando directorio actual para descargas")
                
            os.makedirs(download_dir, exist_ok=True)
            
            # Configurar FIEL
            if not self.fiel:
                self.log_process(" Leyendo certificados...")
                cer_der = open(cer_path, 'rb').read()
                key_der = open(key_path, 'rb').read()
                self.fiel = Fiel(cer_der, key_der, password)
            
            # Autenticación
            if not self.auth:
                self.auth = Autenticacion(self.fiel)
                self.auth.timeout = 60

            self.log_process(" Iniciando proceso de descarga...")
            
            self.progress_bar["value"] = 10
            self.root.update_idletasks()
            
            # Obtener token
            token = self.auth.obtener_token()
            self.log_process(" Token obtenido exitosamente")
            
            self.progress_bar["value"] = 20
            self.root.update_idletasks()

            tipo_descarga = self.download_type_combobox.get()
            estado_seleccionado = self.cfdi_status_combobox.get()
            tipo_solicitud = self.get_tipo_solicitud()
            estado_comprobante = self.get_estado_comprobante()
            fecha_inicial = datetime.datetime.strptime(self.start_date_entry.get(), '%Y-%m-%d').date()
            fecha_final = datetime.datetime.strptime(self.end_date_entry.get(), '%Y-%m-%d').date()
            
            self.log_process(f" Configuración: {tipo_descarga}, Estado: {estado_seleccionado}, Tipo: {tipo_solicitud}")
            
            if tipo_descarga == "Emitidos":
                self.log_process(" Solicitando CFDIs Emitidos (CFDI)...")
                descarga = SolicitaDescargaEmitidos(self.fiel)
                
                solicitud = descarga.solicitar_descarga(
                    token, rfc, fecha_inicial, fecha_final, 
                    rfc_emisor=rfc, 
                    tipo_solicitud=tipo_solicitud,
                    estado_comprobante=estado_comprobante
                )
            else:  # Recibidos
                self.log_process(" Solicitando CFDIs Recibidos (METADATA)...")
                descarga = SolicitaDescargaRecibidos(self.fiel)
                
                # Recibidos usa Metadata y estado_comprobante como string
                solicitud = descarga.solicitar_descarga(
                    token, rfc, fecha_inicial, fecha_final, 
                    rfc_receptor=rfc, 
                    tipo_solicitud=tipo_solicitud,
                    estado_comprobante=estado_comprobante
                )

            self.progress_bar["value"] = 30
            self.root.update_idletasks()

            if solicitud.get('cod_estatus') != '5000':
                error_msg = solicitud.get('mensaje', 'Error desconocido')
                self.log_process(f" Error en la solicitud: {error_msg}")
                messagebox.showerror("Error en solicitud", error_msg)
                return

            self.log_process(f" Solicitud creada: {solicitud['id_solicitud']}")
            
            self.progress_bar["value"] = 40
            self.root.update_idletasks()
            
            attempt_count = 0
            max_auth_retries = 3
            
            while True:
                if self.cancel_requested:
                    self.log_process(" Descarga cancelada por el usuario")
                    break
                    
                try:
                    # Obtener token renovado
                    token_retries = 0
                    while token_retries < max_auth_retries:
                        try:
                            token = self.auth.obtener_token()
                            self.log_process(" Token renovado exitosamente")
                            break
                        except Exception as token_error:
                            token_retries += 1
                            if token_retries >= max_auth_retries:
                                raise
                            self.log_process(f" Error renovando token (intento {token_retries}/{max_auth_retries}): {str(token_error)}")
                            time.sleep(10)
                    
                    verificacion_obj = VerificaSolicitudDescarga(self.fiel)
                    if hasattr(verificacion_obj, 'timeout'):
                        verificacion_obj.timeout = 60
                    
                    verificacion = verificacion_obj.verificar_descarga(token, rfc, solicitud['id_solicitud'])
                    estado_solicitud = int(verificacion['estado_solicitud'])
                    
                    estados = {
                        1: " Aceptada", 
                        2: " En proceso",
                        3: " Terminada",
                        4: " Error", 
                        5: " Rechazada",
                        6: " Vencida"
                    }
                    
                    estado_desc = estados.get(estado_solicitud, f" Estado desconocido ({estado_solicitud})")
                    self.log_process(f" Estado: {estado_desc}")

                    if estado_solicitud <= 2:
                        wait_time = self.smart_polling_wait(attempt_count)
                        self.log_process(f" Esperando {wait_time} segundos...")
                        self.progress_bar["value"] = 50
                        self.root.update_idletasks()
                        
                        for i in range(wait_time):
                            if self.cancel_requested:
                                break
                            time.sleep(1)
                        
                        attempt_count += 1
                        continue
                        
                    elif estado_solicitud == 3:
                        self.log_process(" Solicitud completada")
                        self.progress_bar["value"] = 70
                        self.root.update_idletasks()
                        
                        if 'numero_cfdis' in verificacion:
                            self.log_process(f" CFDIs/Metadatos encontrados: {verificacion['numero_cfdis']}")
                        
                        if 'paquetes' in verificacion and verificacion['paquetes']:
                            self.log_process(f" Paquetes disponibles: {len(verificacion['paquetes'])}")
                            self.download_packages_parallel(token, rfc, verificacion['paquetes'], download_dir)
                            
                            failed_packages = self.validate_download_completeness(verificacion['paquetes'], download_dir)
                            
                            if failed_packages:
                                self.log_process(" Reintentando paquetes fallidos...")
                                self.download_packages_parallel(token, rfc, failed_packages, download_dir)
                                
                        else:
                            self.log_process(" No se encontraron paquetes para descargar")
                        break
                        
                    elif estado_solicitud >= 4:
                        self.log_process(f" Error en la solicitud: {estado_desc}")
                        if 'mensaje' in verificacion:
                            self.log_process(f"Detalle: {verificacion['mensaje']}")
                        messagebox.showerror("Error", f"Estado: {estado_desc}")
                        break
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # Manejo específico de timeouts
                    if 'timed out' in error_msg.lower() or 'timeout' in error_msg.lower():
                        self.log_process(f" Timeout en intento {attempt_count + 1}")
                        attempt_count += 1
                        
                        wait_time = min(30 * (attempt_count), 90)
                        
                        if attempt_count < 5:
                            self.log_process(f"🔄 Esperando {wait_time}s antes de reintentar... ({attempt_count}/5)")
                            for i in range(wait_time):
                                if self.cancel_requested:
                                    break
                                time.sleep(1)
                            
                            # Recrear instancia de autenticación
                            self.auth = Autenticacion(self.fiel)
                            self.auth.timeout = 60
                            continue
                        else:
                            self.log_process(" Máximo de reintentos alcanzado")
                            messagebox.showerror("Error de Conexión", 
                                "No se pudo conectar al servidor del SAT después de 5 intentos.\n"
                                "Por favor, intente más tarde.")
                            break
                    else:
                        self.log_process(f" Error: {error_msg}")
                        logging.error("Error durante verificación", exc_info=True)
                        
                        attempt_count += 1
                        if attempt_count < 3:
                            self.log_process(f" Reintentando en 30 segundos... (intento {attempt_count + 1}/3)")
                            for i in range(30):
                                if self.cancel_requested:
                                    break
                                time.sleep(1)
                            continue
                        else:
                            messagebox.showerror("Error", f"Error después de 3 intentos: {str(e)}")
                            break
                
            if not self.cancel_requested:
                self.progress_bar["value"] = 100
                self.log_process(" Proceso completado exitosamente.")
                messagebox.showinfo("Éxito", "Descarga completada")
            
        except Exception as e:
            self.log_process(f" Error inesperado: {str(e)}")
            logging.error("Error inesperado", exc_info=True)
            messagebox.showerror("Error", str(e))
        finally:
            self.is_downloading = False
            self.cancel_requested = False
            self.download_btn.configure(state='normal')
            self.cancel_btn.configure(state='disabled')

    def clear_fields(self):
        self.rfc_entry.delete(0, tk.END)
        self.cer_entry.delete(0, tk.END)
        self.key_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.download_dir_entry.delete(0, tk.END)
        self.start_date_entry.delete(0, tk.END)
        self.end_date_entry.delete(0, tk.END)
        
        self.fiel = None
        self.auth = None
        self.descarga_masiva_instance = None
        
        # Restablecer estado de la interfaz
        self.download_type_combobox.current(0)
        self.on_download_type_change()
        
        self.log_process(" Campos limpiados")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except tk.TclError as e:
        print(f"No se pudo cargar el ícono: {str(e)}")
    
    app = CFDIDownloaderGUI(root)
    root.mainloop()
