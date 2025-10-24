import tkinter as tk
from tkinter import ttk
import time

class EVMonitorGUI:
    def __init__(self, monitor):
        self.monitor = monitor
        self.root = tk.Tk()
        self.root.title(f"Monitor - Punto de Carga {monitor.cp_id}")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        self.root.resizable(True, True)

        self.bg_dark = "#1a1d2e"
        self.bg_medium = "#22254a"
        self.bg_light = "#2a2d4a"
        self.bg_card = "#252841"
        self.text_primary = "#ffffff"
        self.text_secondary = "#b8b9cf"
        self.text_dim = "#6c6f93"
        self.accent_blue = "#4facfe"
        self.accent_cyan = "#00f2fe"
        self.accent_purple = "#9b59b6"
        self.accent_pink = "#e74c3c"
        self.success = "#2ecc71"
        self.warning = "#f39c12"
        self.error = "#e74c3c"
        self.border = "#3a3d5c"
        
        self.root.configure(bg=self.bg_dark)
        self.log_messages = []
        self._create_widgets()
        self._start_update_loop()
        
    def _create_widgets(self):
        main_container = tk.Frame(self.root, bg=self.bg_dark)
        main_container.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(main_container, bg=self.bg_medium, width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        self._create_sidebar(sidebar)

        content = tk.Frame(main_container, bg=self.bg_dark)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._create_content(content)
        
    def _create_sidebar(self, parent):
        logo_frame = tk.Frame(parent, bg=self.bg_medium)
        logo_frame.pack(fill=tk.X, padx=20, pady=30)
        
        logo_text = tk.Label(
            logo_frame,
            text="📡",
            font=("Segoe UI", 32),
            bg=self.bg_medium,
            fg=self.accent_cyan
        )
        logo_text.pack()
        
        title = tk.Label(
            logo_frame,
            text="CP Monitor",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_medium,
            fg=self.text_primary
        )
        title.pack(pady=(5, 0))
        
        subtitle = tk.Label(
            logo_frame,
            text=self.monitor.cp_id,
            font=("Segoe UI", 11),
            bg=self.bg_medium,
            fg=self.text_dim
        )
        subtitle.pack()

        status_frame = tk.Frame(parent, bg=self.bg_light)
        status_frame.pack(fill=tk.X, padx=15, pady=(20, 0))
        
        status_content = tk.Frame(status_frame, bg=self.bg_light)
        status_content.pack(fill=tk.X, padx=15, pady=15)
        
        status_label = tk.Label(
            status_content,
            text="Estado del CP",
            font=("Segoe UI", 9),
            bg=self.bg_light,
            fg=self.text_dim
        )
        status_label.pack(anchor=tk.W)
        
        status_value_frame = tk.Frame(status_content, bg=self.bg_light)
        status_value_frame.pack(anchor=tk.W, pady=(5, 0))
        
        self.status_indicator = tk.Label(
            status_value_frame,
            text="●",
            font=("Segoe UI", 16),
            bg=self.bg_light,
            fg=self.text_dim
        )
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(
            status_value_frame,
            text="INICIANDO",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.text_primary
        )
        self.status_text.pack(side=tk.LEFT, padx=(8, 0))
        
        tk.Label(
            parent,
            text="Conexiones",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_secondary
        ).pack(anchor=tk.W, padx=20, pady=(25, 10))
        
        self._create_sidebar_info(parent, "Engine", "Desconectado", "engine_status")
        self._create_sidebar_info(parent, "Central", "Desconectado", "central_status")

        tk.Label(
            parent,
            text="Control",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_secondary
        ).pack(anchor=tk.W, padx=20, pady=(25, 10))
        
        self._create_sidebar_info(parent, "Modo", "Automático", "control_mode")
        
    def _create_sidebar_info(self, parent, label, value, var_name):
        frame = tk.Frame(parent, bg=self.bg_medium)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(
            frame,
            text=label,
            font=("Segoe UI", 9),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        value_label = tk.Label(
            frame,
            text=value,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_secondary
        )
        value_label.pack(anchor=tk.W, pady=(2, 0))
        
        setattr(self, var_name, value_label)
        
    def _create_content(self, parent):
        header = tk.Frame(parent, bg=self.bg_dark, height=80)
        header.pack(fill=tk.X, padx=30, pady=(20, 0))
        header.pack_propagate(False)
        
        header_content = tk.Frame(header, bg=self.bg_dark)
        header_content.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(
            header_content,
            text="Panel de Monitoreo",
            font=("Segoe UI", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_primary
        ).pack(side=tk.LEFT)
        
        content_scroll = tk.Frame(parent, bg=self.bg_dark)
        content_scroll.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        top_row = tk.Frame(content_scroll, bg=self.bg_dark)
        top_row.pack(fill=tk.X, pady=(0, 20))
        
        self._create_connection_cards(top_row)

        bottom_row = tk.Frame(content_scroll, bg=self.bg_dark)
        bottom_row.pack(fill=tk.BOTH, expand=True)
        
        self._create_log_card(bottom_row)
        
    def _create_connection_cards(self, parent):
        engine_card = tk.Frame(parent, bg=self.bg_card)
        engine_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        engine_content = tk.Frame(engine_card, bg=self.bg_card)
        engine_content.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        tk.Label(
            engine_content,
            text="Conexión Engine",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        engine_status_frame = tk.Frame(engine_content, bg=self.bg_card)
        engine_status_frame.pack(anchor=tk.W, pady=(10, 0))
        
        self.engine_indicator = tk.Label(
            engine_status_frame,
            text="●",
            font=("Segoe UI", 24),
            bg=self.bg_card,
            fg=self.error
        )
        self.engine_indicator.pack(side=tk.LEFT)
        
        engine_info = tk.Frame(engine_status_frame, bg=self.bg_card)
        engine_info.pack(side=tk.LEFT, padx=(10, 0))
        
        self.engine_status_label = tk.Label(
            engine_info,
            text="Desconectado",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        )
        self.engine_status_label.pack(anchor=tk.W)
        
        self.engine_address = tk.Label(
            engine_info,
            text=f"{self.monitor.engine_ip}:{self.monitor.engine_port}",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.text_dim
        )
        self.engine_address.pack(anchor=tk.W)

        central_card = tk.Frame(parent, bg=self.bg_card)
        central_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        central_content = tk.Frame(central_card, bg=self.bg_card)
        central_content.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        tk.Label(
            central_content,
            text="Conexión Central",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        central_status_frame = tk.Frame(central_content, bg=self.bg_card)
        central_status_frame.pack(anchor=tk.W, pady=(10, 0))
        
        self.central_indicator = tk.Label(
            central_status_frame,
            text="●",
            font=("Segoe UI", 24),
            bg=self.bg_card,
            fg=self.error
        )
        self.central_indicator.pack(side=tk.LEFT)
        
        central_info = tk.Frame(central_status_frame, bg=self.bg_card)
        central_info.pack(side=tk.LEFT, padx=(10, 0))
        
        self.central_status_label = tk.Label(
            central_info,
            text="Desconectado",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        )
        self.central_status_label.pack(anchor=tk.W)
        
        self.central_address = tk.Label(
            central_info,
            text=f"{self.monitor.central_ip}:{self.monitor.central_port}",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.text_dim
        )
        self.central_address.pack(anchor=tk.W)
        
    def _create_log_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card)
        card.pack(fill=tk.BOTH, expand=True)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        title_frame = tk.Frame(content, bg=self.bg_card)
        title_frame.pack(fill=tk.X)
        
        tk.Label(
            title_frame,
            text="Registro de Eventos",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            title_frame,
            text="Limpiar",
            font=("Segoe UI", 9),
            bg=self.bg_light,
            fg=self.text_secondary,
            activebackground=self.bg_light,
            activeforeground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._clear_log,
            padx=15,
            pady=5
        )
        clear_btn.pack(side=tk.RIGHT)
        
        tk.Label(
            content,
            text="Monitoreo en tiempo real del estado del punto de carga",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W, pady=(5, 15))

        log_container = tk.Frame(content, bg=self.bg_card)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_container,
            font=("Consolas", 9),
            bg=self.bg_light,
            fg=self.text_secondary,
            relief=tk.FLAT,
            bd=0,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("ERROR", foreground=self.error)
        self.log_text.tag_config("OK", foreground=self.success)
        self.log_text.tag_config("INFO", foreground=self.accent_blue)
        self.log_text.tag_config("CENTRAL", foreground=self.accent_cyan)
        self.log_text.tag_config("MONITOR", foreground=self.accent_purple)
        
    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def log_message(self, message):
        try:
            if not self.root.winfo_exists():
                return
                
            timestamp = time.strftime("%H:%M:%S")
            
            self.log_text.config(state=tk.NORMAL)
            
            if "[ERROR]" in message:
                self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
                self.log_text.insert(tk.END, message + "\n", "ERROR")
            elif "[MONITOR]" in message:
                self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
                self.log_text.insert(tk.END, message + "\n", "MONITOR")
            elif "[CENTRAL]" in message:
                self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
                self.log_text.insert(tk.END, message + "\n", "CENTRAL")
            elif "Conectado" in message or "Reconectado" in message or "activo" in message:
                self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
                self.log_text.insert(tk.END, message + "\n", "OK")
            else:
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except:
            pass
        
    def _start_update_loop(self):
        self._update_status()
        
    def _update_status(self):
        try:
            if not self.root.winfo_exists():
                return
        except:
            return
            
        with self.monitor.lock:
            last_status = self.monitor.last_status
            manually_stopped = self.monitor.manually_stopped
            
        engine_connected = self.monitor.engine_client is not None
        central_connected = self.monitor.central_client is not None
        
        if engine_connected:
            self.engine_indicator.config(fg=self.success)
            self.engine_status_label.config(text="Conectado")
            self.engine_status.config(text="Conectado", fg=self.success)
        else:
            self.engine_indicator.config(fg=self.error)
            self.engine_status_label.config(text="Desconectado")
            self.engine_status.config(text="Desconectado", fg=self.error)
        
        if central_connected:
            self.central_indicator.config(fg=self.success)
            self.central_status_label.config(text="Conectado")
            self.central_status.config(text="Conectado", fg=self.success)
        else:
            self.central_indicator.config(fg=self.error)
            self.central_status_label.config(text="Desconectado")
            self.central_status.config(text="Desconectado", fg=self.error)
        
        if last_status == "OK":
            self.status_indicator.config(fg=self.success)
            self.status_text.config(text="OPERATIVO")
        elif last_status == "SUMINISTRANDO":
            self.status_indicator.config(fg=self.warning)
            self.status_text.config(text="SUMINISTRANDO")
        elif last_status == "AVERIA":
            self.status_indicator.config(fg=self.error)
            self.status_text.config(text="AVERÍA")
        elif last_status == "PARADO":
            self.status_indicator.config(fg=self.text_dim)
            self.status_text.config(text="PARADO")
        else:
            self.status_indicator.config(fg=self.text_dim)
            self.status_text.config(text="INICIANDO")
        
        if manually_stopped:
            self.control_mode.config(text="Manual (Parado)", fg=self.warning)
        else:
            self.control_mode.config(text="Automático", fg=self.success)
        
        try:
            self.root.after(500, self._update_status)
        except:
            pass
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.root.mainloop()
        except:
            pass
        
    def _on_close(self):
        try:
            self.root.destroy()
        except:
            pass
        self.monitor.gui = None