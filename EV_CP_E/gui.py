import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class EVChargingGUI:
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title(f"Punto de Carga - {engine.cp_id}")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        
        # Color scheme - Professional dark theme
        self.bg_primary = "#0a0e27"
        self.bg_secondary = "#151932"
        self.bg_card = "#1a1f3a"
        self.bg_input = "#232940"
        
        self.text_primary = "#e4e4e7"
        self.text_secondary = "#a1a1aa"
        self.text_dim = "#71717a"
        
        self.accent_blue = "#3b82f6"
        self.accent_green = "#10b981"
        self.accent_yellow = "#f59e0b"
        self.accent_red = "#ef4444"
        
        self.root.configure(bg=self.bg_primary)
        
        self._create_widgets()
        self._start_update_loop()
        
    def _create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.bg_secondary, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_content = tk.Frame(header, bg=self.bg_secondary)
        header_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=15)
        
        title_label = tk.Label(
            header_content,
            text=f"Punto de Carga {self.engine.cp_id}",
            font=("Segoe UI", 22, "bold"),
            bg=self.bg_secondary,
            fg=self.text_primary
        )
        title_label.pack(side=tk.LEFT)
        
        # Status indicator in header
        self.header_status = tk.Label(
            header_content,
            text="OPERATIVO",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_green,
            fg=self.bg_primary,
            padx=15,
            pady=5
        )
        self.header_status.pack(side=tk.RIGHT)
        
        # Main content
        main_container = tk.Frame(self.root, bg=self.bg_primary)
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Left panel - Status and metrics
        left_panel = tk.Frame(main_container, bg=self.bg_primary)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        
        self._create_system_status_card(left_panel)
        self._create_metrics_card(left_panel)
        
        # Right panel - Controls
        right_panel = tk.Frame(main_container, bg=self.bg_primary)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        self._create_control_card(right_panel)
        self._create_supply_info_card(right_panel)
        
    def _create_system_status_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 20))
        
        title = tk.Label(
            card,
            text="Estado del Sistema",
            font=("Segoe UI", 13, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=20, pady=(20, 15))
        
        # Grid for status items
        status_grid = tk.Frame(card, bg=self.bg_card)
        status_grid.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Kafka status
        self._create_status_item(status_grid, "Conexión Kafka", 0)
        self.kafka_status_indicator = tk.Label(
            status_grid,
            text="●",
            font=("Segoe UI", 16),
            bg=self.bg_card,
            fg=self.accent_green
        )
        self.kafka_status_indicator.grid(row=0, column=1, sticky="e", padx=(10, 0))
        
        self.kafka_status_text = tk.Label(
            status_grid,
            text="Conectado",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_card,
            fg=self.accent_green
        )
        self.kafka_status_text.grid(row=0, column=2, sticky="w", padx=(5, 0))
        
        # Monitor status
        self._create_status_item(status_grid, "Servidor Monitor", 1)
        monitor_text = f"{self.engine.monitor_ip}:{self.engine.monitor_port}"
        self.monitor_status_text = tk.Label(
            status_grid,
            text=monitor_text,
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary
        )
        self.monitor_status_text.grid(row=1, column=1, columnspan=2, sticky="e", padx=(10, 0))
        
        # Price info
        self._create_status_item(status_grid, "Tarifa", 2)
        price_text = f"{self.engine.price:.3f} EUR/kWh"
        self.price_status_text = tk.Label(
            status_grid,
            text=price_text,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_card,
            fg=self.accent_blue
        )
        self.price_status_text.grid(row=2, column=1, columnspan=2, sticky="e", padx=(10, 0))
        
        status_grid.grid_columnconfigure(0, weight=1)
        
    def _create_status_item(self, parent, text, row):
        label = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim,
            anchor=tk.W
        )
        label.grid(row=row, column=0, sticky="w", pady=8)
        
    def _create_metrics_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(
            card,
            text="Métricas de Suministro",
            font=("Segoe UI", 13, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=20, pady=(20, 5))
        
        self.supply_driver_label = tk.Label(
            card,
            text="Sin suministro activo",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim,
            anchor=tk.W
        )
        self.supply_driver_label.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Metrics grid
        metrics_container = tk.Frame(card, bg=self.bg_card)
        metrics_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Consumption metric
        consumption_frame = self._create_metric_box(
            metrics_container, 
            "Consumo Total",
            "0.00",
            "kWh"
        )
        consumption_frame.pack(fill=tk.X, pady=(0, 12))
        self.consumption_value = consumption_frame.winfo_children()[1]
        
        # Price metric
        price_frame = self._create_metric_box(
            metrics_container,
            "Importe Total",
            "0.00",
            "EUR"
        )
        price_frame.pack(fill=tk.X, pady=(0, 12))
        self.price_value = price_frame.winfo_children()[1]
        
        # Time metric
        time_frame = self._create_metric_box(
            metrics_container,
            "Tiempo Transcurrido",
            "0",
            "segundos"
        )
        time_frame.pack(fill=tk.X)
        self.time_value = time_frame.winfo_children()[1]
        
    def _create_metric_box(self, parent, label, value, unit):
        container = tk.Frame(parent, bg=self.bg_input)
        
        label_text = tk.Label(
            container,
            text=label,
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.text_dim,
            anchor=tk.W
        )
        label_text.pack(fill=tk.X, padx=15, pady=(12, 5))
        
        value_container = tk.Frame(container, bg=self.bg_input)
        value_container.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        value_label = tk.Label(
            value_container,
            text=value,
            font=("Segoe UI", 22, "bold"),
            bg=self.bg_input,
            fg=self.text_primary,
            anchor=tk.W
        )
        value_label.pack(side=tk.LEFT)
        
        unit_label = tk.Label(
            value_container,
            text=unit,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_secondary,
            anchor=tk.W
        )
        unit_label.pack(side=tk.LEFT, padx=(8, 0), pady=(8, 0))
        
        return container
        
    def _create_control_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 20))
        
        title = tk.Label(
            card,
            text="Panel de Control",
            font=("Segoe UI", 13, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=20, pady=(20, 15))
        
        # Driver ID input
        input_label = tk.Label(
            card,
            text="ID del Conductor",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.text_dim,
            anchor=tk.W
        )
        input_label.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        self.driver_entry = tk.Entry(
            card,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0
        )
        self.driver_entry.pack(fill=tk.X, padx=20, ipady=10, ipadx=12)
        
        # Control buttons
        btn_container = tk.Frame(card, bg=self.bg_card)
        btn_container.pack(fill=tk.X, padx=20, pady=(15, 20))
        
        self.start_btn = self._create_action_button(
            btn_container,
            "Solicitar Suministro",
            self._on_request_supply,
            self.accent_green
        )
        self.start_btn.pack(fill=tk.X, pady=(0, 10))
        
        self.stop_btn = self._create_action_button(
            btn_container,
            "Finalizar Suministro",
            self._on_stop_supply,
            self.accent_red
        )
        self.stop_btn.pack(fill=tk.X)
        self.stop_btn.config(state=tk.DISABLED)
        
    def _create_supply_info_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(
            card,
            text="Gestión del Sistema",
            font=("Segoe UI", 13, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=20, pady=(20, 15))
        
        # Breakdown controls
        breakdown_label = tk.Label(
            card,
            text="Simulación de Averías",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.text_dim,
            anchor=tk.W
        )
        breakdown_label.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        btn_container = tk.Frame(card, bg=self.bg_card)
        btn_container.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.breakdown_btn = self._create_action_button(
            btn_container,
            "Simular Avería",
            self._on_breakdown,
            self.accent_yellow,
            secondary=True
        )
        self.breakdown_btn.pack(fill=tk.X, pady=(0, 10))
        
        self.repair_btn = self._create_action_button(
            btn_container,
            "Reparar Sistema",
            self._on_repair,
            self.accent_blue,
            secondary=True
        )
        self.repair_btn.pack(fill=tk.X)
        self.repair_btn.config(state=tk.DISABLED)
        
    def _create_action_button(self, parent, text, command, color, secondary=False):
        if secondary:
            bg = self.bg_input
            fg = color
            active_bg = self.bg_secondary
        else:
            bg = color
            fg = self.bg_primary
            active_bg = color
            
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg if secondary else self.bg_primary,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=command
        )
        
        if not secondary:
            btn.bind("<Enter>", lambda e: btn.config(bg=self._adjust_brightness(color, 1.1)))
            btn.bind("<Leave>", lambda e: btn.config(bg=color))
        else:
            btn.bind("<Enter>", lambda e: btn.config(bg=self.bg_secondary))
            btn.bind("<Leave>", lambda e: btn.config(bg=self.bg_input))
            
        return btn
    
    def _adjust_brightness(self, color, factor):
        # Simple brightness adjustment
        return color
        
    def _on_request_supply(self):
        driver_id = self.driver_entry.get().strip()
        if not driver_id:
            messagebox.showwarning("Advertencia", "Por favor ingrese un ID de conductor")
            return
            
        with self.engine.lock:
            if self.engine.charging:
                messagebox.showerror("Error", "El punto de carga ya está suministrando energía")
                return
        
        request = {'conductor_id': driver_id, 'cp_id': self.engine.cp_id, 'origen': 'GUI'}
        
        try:
            self.engine.producer.send('solicitudes_suministro', request)
            self.engine.producer.flush()
            self.driver_entry.delete(0, tk.END)
        except Exception:
            messagebox.showerror("Error", "No se pudo enviar la solicitud. Verifique la conexión a Kafka.")
            self.engine._reconnect_kafka()
            
    def _on_stop_supply(self):
        with self.engine.lock:
            if self.engine.charging:
                self.engine.charging = False
            else:
                messagebox.showinfo("Información", "No hay ningún suministro activo")
                
    def _on_breakdown(self):
        with self.engine.lock:
            self.engine.breakdown_status = True
        self.breakdown_btn.config(state=tk.DISABLED)
        self.repair_btn.config(state=tk.NORMAL)
        
    def _on_repair(self):
        with self.engine.lock:
            self.engine.breakdown_status = False
        self.breakdown_btn.config(state=tk.NORMAL)
        self.repair_btn.config(state=tk.DISABLED)
        
    def _start_update_loop(self):
        self._update_status()
        
    def _update_status(self):
        if not self.root.winfo_exists():
            return
            
        with self.engine.lock:
            breakdown = self.engine.breakdown_status
            charging = self.engine.charging
            driver = self.engine.current_driver
            
        # Update header status
        if breakdown:
            self.header_status.config(text="AVERÍA", bg=self.accent_red)
        elif charging:
            self.header_status.config(text="SUMINISTRANDO", bg=self.accent_yellow)
        else:
            self.header_status.config(text="OPERATIVO", bg=self.accent_green)
            
        # Update Kafka status
        if self.engine.producer:
            self.kafka_status_indicator.config(fg=self.accent_green)
            self.kafka_status_text.config(text="Conectado", fg=self.accent_green)
        else:
            self.kafka_status_indicator.config(fg=self.accent_red)
            self.kafka_status_text.config(text="Desconectado", fg=self.accent_red)
        
        # Update supply info
        if charging and driver:
            self.supply_driver_label.config(
                text=f"Suministrando a: {driver}",
                fg=self.text_secondary
            )
            self.stop_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.DISABLED)
        else:
            self.supply_driver_label.config(
                text="Sin suministro activo",
                fg=self.text_dim
            )
            self.stop_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
            self.consumption_value.config(text="0.00")
            self.price_value.config(text="0.00")
            self.time_value.config(text="0")
            
        self.root.after(500, self._update_status)
        
    def _update_metrics(self, consumed_kwh, total_price, duration):
        self.consumption_value.config(text=f"{consumed_kwh:.2f}")
        self.price_value.config(text=f"{total_price:.2f}")
        self.time_value.config(text=f"{duration}")
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        if messagebox.askokcancel("Salir", "¿Desea cerrar el punto de carga?"):
            self.engine.end()
            self.root.destroy()