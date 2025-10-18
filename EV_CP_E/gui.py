import tkinter as tk
from tkinter import messagebox
import time

class EVChargingGUI:
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title(f"Sistema de Gestión - Punto de Carga {engine.cp_id}")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)
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
            text="⚡",
            font=("Segoe UI", 32),
            bg=self.bg_medium,
            fg=self.accent_cyan
        )
        logo_text.pack()
        
        title = tk.Label(
            logo_frame,
            text="EV Charging",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_medium,
            fg=self.text_primary
        )
        title.pack(pady=(5, 0))
        
        subtitle = tk.Label(
            logo_frame,
            text=self.engine.cp_id,
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
            text="Estado del Sistema",
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
            fg=self.success
        )
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(
            status_value_frame,
            text="OPERATIVO",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.text_primary
        )
        self.status_text.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(
            parent,
            text="Información",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_secondary
        ).pack(anchor=tk.W, padx=20, pady=(25, 10))
        
        self._create_sidebar_info(parent, "Kafka", "Conectado", "kafka_status")
        self._create_sidebar_info(parent, "Monitor", f"{self.engine.monitor_port}", "monitor_status")
        self._create_sidebar_info(parent, "Tarifa", f"{self.engine.price:.4f} €/kWh", "price_status")
        
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
            text="Panel de Control",
            font=("Segoe UI", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_primary
        ).pack(side=tk.LEFT)

        content_scroll = tk.Frame(parent, bg=self.bg_dark)
        content_scroll.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        top_row = tk.Frame(content_scroll, bg=self.bg_dark)
        top_row.pack(fill=tk.X, pady=(0, 20))
        
        self._create_metric_cards(top_row)

        bottom_row = tk.Frame(content_scroll, bg=self.bg_dark)
        bottom_row.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(bottom_row, bg=self.bg_dark)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self._create_supply_control_card(left_panel)

        right_panel = tk.Frame(bottom_row, bg=self.bg_dark)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self._create_maintenance_card(right_panel)
        
    def _create_metric_cards(self, parent):
        metrics = [
            ("Consumo", "0.00", "kWh", "consumption_metric", self.accent_cyan),
            ("Importe", "0.00", "EUR", "price_metric", self.accent_blue),
            ("Tiempo", "0", "seg", "time_metric", self.accent_purple),
            ("Conductor", "---", "", "driver_metric", self.accent_pink)
        ]
        
        for i, (label, value, unit, var_name, color) in enumerate(metrics):
            card = self._create_gradient_metric_card(parent, label, value, unit, color)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15) if i < 3 else (0, 0))
            
    def _create_gradient_metric_card(self, parent, label, value, unit, color):
        card = tk.Frame(parent, bg=self.bg_card)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        tk.Label(
            content,
            text=label,
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W)

        value_frame = tk.Frame(content, bg=self.bg_card)
        value_frame.pack(anchor=tk.W, pady=(10, 0))
        
        value_label = tk.Label(
            value_frame,
            text=value,
            font=("Segoe UI", 32, "bold"),
            bg=self.bg_card,
            fg=color
        )
        value_label.pack(side=tk.LEFT)
        
        if unit:
            tk.Label(
                value_frame,
                text=unit,
                font=("Segoe UI", 12),
                bg=self.bg_card,
                fg=self.text_secondary
            ).pack(side=tk.LEFT, padx=(8, 0), pady=(12, 0))

        if label == "Consumo":
            self.consumption_value = value_label
        elif label == "Importe":
            self.price_value = value_label
        elif label == "Tiempo":
            self.time_value = value_label
        elif label == "Conductor":
            self.driver_value = value_label
            
        return card
        
    def _create_supply_control_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card)
        card.pack(fill=tk.BOTH, expand=True)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        tk.Label(
            content,
            text="Control de Suministro",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(anchor=tk.W)
        
        tk.Label(
            content,
            text="Gestión de solicitudes y suministros activos",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W, pady=(5, 20))

        info_frame = tk.Frame(content, bg=self.bg_light)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info_content = tk.Frame(info_frame, bg=self.bg_light)
        info_content.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            info_content,
            text="Suministro Actual",
            font=("Segoe UI", 9),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        self.current_supply_label = tk.Label(
            info_content,
            text="Sin suministro activo",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.text_secondary
        )
        self.current_supply_label.pack(anchor=tk.W, pady=(5, 0))

        tk.Label(
            content,
            text="ID del Conductor",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary
        ).pack(anchor=tk.W, pady=(0, 8))
        
        self.driver_entry = tk.Entry(
            content,
            font=("Segoe UI", 12),
            bg=self.bg_light,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0
        )
        self.driver_entry.pack(fill=tk.X, ipady=12, ipadx=15)

        button_frame = tk.Frame(content, bg=self.bg_card)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.start_btn = self._create_gradient_button(
            button_frame,
            "Solicitar Suministro",
            self._on_request_supply,
            self.accent_blue,
            self.accent_cyan
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.stop_btn = self._create_gradient_button(
            button_frame,
            "Finalizar Suministro",
            self._on_stop_supply,
            self.error,
            self.accent_pink
        )
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.stop_btn.config(state=tk.DISABLED, bg=self.border)
        
    def _create_maintenance_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card)
        card.pack(fill=tk.BOTH, expand=True)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        tk.Label(
            content,
            text="Mantenimiento del Sistema",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(anchor=tk.W)
        
        tk.Label(
            content,
            text="Simulación de estados y diagnóstico",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W, pady=(5, 20))

        status_box = tk.Frame(content, bg=self.bg_light)
        status_box.pack(fill=tk.X, pady=(0, 20))
        
        status_content = tk.Frame(status_box, bg=self.bg_light)
        status_content.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            status_content,
            text="Estado de Mantenimiento",
            font=("Segoe UI", 9),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        self.maintenance_status = tk.Label(
            status_content,
            text="Sistema operativo",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.success
        )
        self.maintenance_status.pack(anchor=tk.W, pady=(5, 0))

        tk.Label(
            content,
            text="Simulación de Avería",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary
        ).pack(anchor=tk.W, pady=(0, 8))
        
        self.breakdown_btn = self._create_gradient_button(
            content,
            "Simular Avería",
            self._on_breakdown,
            self.warning,
            "#f1c40f"
        )
        self.breakdown_btn.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            content,
            text="Reparación del Sistema",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary
        ).pack(anchor=tk.W, pady=(0, 8))
        
        self.repair_btn = self._create_gradient_button(
            content,
            "Reparar Sistema",
            self._on_repair,
            self.success,
            "#27ae60"
        )
        self.repair_btn.pack(fill=tk.X)
        self.repair_btn.config(state=tk.DISABLED, bg=self.border)
        
    def _create_gradient_button(self, parent, text, command, color1, color2):
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 11, "bold"),
            bg=color1,
            fg="#ffffff",
            activebackground=color2,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=command,
            height=2
        )
        return btn
        
    def _on_request_supply(self):
        driver_id = self.driver_entry.get().strip()
        if not driver_id:
            return
            
        with self.engine.lock:
            if self.engine.charging:
                return
            
            if self.engine.breakdown_status:
                return
        
        request = {'conductor_id': driver_id, 'cp_id': self.engine.cp_id, 'origen': 'GUI'}
        
        try:
            if not self.engine.producer:
                return
                
            self.engine.producer.send('solicitudes_suministro', request)
            self.engine.producer.flush()
        except Exception:
            pass
            
    def _on_stop_supply(self):
        with self.engine.lock:
            if not self.engine.charging:
                return
                
            self.engine.charging = False
                
    def _on_breakdown(self):
        with self.engine.lock:
            self.engine.breakdown_status = True
            
        self.breakdown_btn.config(state=tk.DISABLED, bg=self.border)
        self.repair_btn.config(state=tk.NORMAL, bg=self.success)
        self.maintenance_status.config(text="Avería detectada", fg=self.error)
        
    def _on_repair(self):
        with self.engine.lock:
            self.engine.breakdown_status = False
            
        self.breakdown_btn.config(state=tk.NORMAL, bg=self.warning)
        self.repair_btn.config(state=tk.DISABLED, bg=self.border)
        self.maintenance_status.config(text="Sistema operativo", fg=self.success)
        
    def _start_update_loop(self):
        self._update_status()
        
    def _update_status(self):
        try:
            if not self.root.winfo_exists():
                return
        except:
            return
            
        with self.engine.lock:
            breakdown = self.engine.breakdown_status
            charging = self.engine.charging
            driver = self.engine.current_driver

        if breakdown:
            self.status_indicator.config(fg=self.error)
            self.status_text.config(text="AVERÍA")
        elif charging:
            self.status_indicator.config(fg=self.warning)
            self.status_text.config(text="SUMINISTRANDO")
        else:
            self.status_indicator.config(fg=self.success)
            self.status_text.config(text="OPERATIVO")

        kafka_text = "Conectado" if self.engine.producer else "Desconectado"
        kafka_color = self.success if self.engine.producer else self.error
        self.kafka_status.config(text=kafka_text, fg=kafka_color)
        
        if charging and driver:
            self.current_supply_label.config(text=f"Conductor: {driver}", fg=self.text_primary)
            self.driver_value.config(text=driver)
            
            self.driver_entry.config(state=tk.DISABLED, disabledbackground=self.bg_light, disabledforeground=self.text_dim)
            self.start_btn.config(state=tk.DISABLED, bg=self.border)
            
            self.stop_btn.config(state=tk.NORMAL, bg=self.error)
            
            if breakdown:
                self.breakdown_btn.config(state=tk.DISABLED, bg=self.border)
        else:
            self.current_supply_label.config(text="Sin suministro activo", fg=self.text_dim)
            self.driver_value.config(text="---")
            
            if breakdown:
                self.driver_entry.config(state=tk.DISABLED, disabledbackground=self.bg_light, disabledforeground=self.text_dim)
                self.start_btn.config(state=tk.DISABLED, bg=self.border)
            else:
                self.driver_entry.config(state=tk.NORMAL, bg=self.bg_light)
                if self.engine.producer:
                    self.start_btn.config(state=tk.NORMAL, bg=self.accent_blue)
                else:
                    self.start_btn.config(state=tk.DISABLED, bg=self.border)
            
            self.stop_btn.config(state=tk.DISABLED, bg=self.border)
            
            self.consumption_value.config(text="0.00")
            self.price_value.config(text="0.00")
            self.time_value.config(text="0")
        
        try:
            self.root.after(500, self._update_status)
        except:
            pass
        
    def _update_metrics(self, consumed_kwh, total_price, duration):
        try:
            if self.root.winfo_exists():
                self.consumption_value.config(text=f"{consumed_kwh:.2f}")
                self.price_value.config(text=f"{total_price:.2f}")
                self.time_value.config(text=f"{duration}")
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
        self.engine.gui = None