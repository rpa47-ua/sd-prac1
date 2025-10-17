import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class EVChargingGUI:
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title(f"Punto de Carga - {engine.cp_id}")
        self.root.geometry("850x720")
        self.root.resizable(True, True)
        
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.success_color = "#a6e3a1"
        self.warning_color = "#f9e2af"
        self.error_color = "#f38ba8"
        self.card_color = "#313244"
        
        self.root.configure(bg=self.bg_color)
        
        self._create_widgets()
        self._start_update_loop()
        
    def _create_widgets(self):
        header = tk.Frame(self.root, bg=self.accent_color, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text=f"🔌 Punto de Carga {self.engine.cp_id}",
            font=("Segoe UI", 24, "bold"),
            bg=self.accent_color,
            fg="#1e1e2e"
        )
        title_label.pack(pady=20)
        
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        left_panel = tk.Frame(main_container, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self._create_status_card(left_panel)
        self._create_supply_card(left_panel)
        
        right_panel = tk.Frame(main_container, bg=self.bg_color)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self._create_control_card(right_panel)
        self._create_log_card(right_panel)
        
    def _create_status_card(self, parent):
        card = tk.Frame(parent, bg=self.card_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(
            card,
            text="📊 Estado del Sistema",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_color,
            fg=self.fg_color,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        self.status_label = tk.Label(
            card,
            text="● OK",
            font=("Segoe UI", 16, "bold"),
            bg=self.card_color,
            fg=self.success_color
        )
        self.status_label.pack(pady=(5, 10))
        
        info_frame = tk.Frame(card, bg=self.card_color)
        info_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self._create_info_row(info_frame, "Kafka:", "Conectado", "kafka_status")
        self._create_info_row(info_frame, "Monitor:", f"{self.engine.monitor_ip}:{self.engine.monitor_port}", "monitor_status")
        self._create_info_row(info_frame, "Precio:", f"{self.engine.price:.3f} EUR/kWh", "price_label")
        
    def _create_info_row(self, parent, label_text, value_text, var_name):
        row = tk.Frame(parent, bg=self.card_color)
        row.pack(fill=tk.X, pady=3)
        
        label = tk.Label(
            row,
            text=label_text,
            font=("Segoe UI", 10),
            bg=self.card_color,
            fg=self.fg_color,
            anchor=tk.W,
            width=12
        )
        label.pack(side=tk.LEFT)
        
        value = tk.Label(
            row,
            text=value_text,
            font=("Segoe UI", 10, "bold"),
            bg=self.card_color,
            fg=self.accent_color,
            anchor=tk.W
        )
        value.pack(side=tk.LEFT, fill=tk.X, expand=True)
        setattr(self, var_name, value)
        
    def _create_supply_card(self, parent):
        card = tk.Frame(parent, bg=self.card_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(
            card,
            text="⚡ Suministro Actual",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_color,
            fg=self.fg_color,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        self.supply_status = tk.Label(
            card,
            text="Sin suministro activo",
            font=("Segoe UI", 11),
            bg=self.card_color,
            fg=self.fg_color,
            wraplength=300,
            justify=tk.LEFT
        )
        self.supply_status.pack(fill=tk.X, padx=15, pady=(5, 15))
        
        metrics_frame = tk.Frame(card, bg=self.card_color)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.consumption_label = self._create_metric(
            metrics_frame,
            "Consumo",
            "0.00 kWh",
            0
        )
        
        self.price_current_label = self._create_metric(
            metrics_frame,
            "Importe",
            "0.00 EUR",
            1
        )
        
        # Tiempo
        self.time_label = self._create_metric(
            metrics_frame,
            "Tiempo",
            "0s",
            2
        )
        
    def _create_metric(self, parent, title, value, row):
        frame = tk.Frame(parent, bg="#45475a", relief=tk.FLAT, bd=0)
        frame.grid(row=row, column=0, sticky="ew", pady=5)
        parent.grid_columnconfigure(0, weight=1)
        
        title_label = tk.Label(
            frame,
            text=title,
            font=("Segoe UI", 9),
            bg="#45475a",
            fg=self.fg_color,
            anchor=tk.W
        )
        title_label.pack(fill=tk.X, padx=10, pady=(8, 2))
        
        value_label = tk.Label(
            frame,
            text=value,
            font=("Segoe UI", 16, "bold"),
            bg="#45475a",
            fg=self.accent_color,
            anchor=tk.W
        )
        value_label.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        return value_label
        
    def _create_control_card(self, parent):
        card = tk.Frame(parent, bg=self.card_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(
            card,
            text="🎮 Controles",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_color,
            fg=self.fg_color,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        input_frame = tk.Frame(card, bg=self.card_color)
        input_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        input_label = tk.Label(
            input_frame,
            text="ID Conductor:",
            font=("Segoe UI", 10),
            bg=self.card_color,
            fg=self.fg_color
        )
        input_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.driver_entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 11),
            bg="#45475a",
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.FLAT,
            bd=0
        )
        self.driver_entry.pack(fill=tk.X, ipady=8, ipadx=10)
        
        btn_frame = tk.Frame(card, bg=self.card_color)
        btn_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        
        self.start_btn = self._create_button(
            btn_frame,
            "▶ Solicitar Suministro",
            self._on_request_supply,
            self.success_color
        )
        self.start_btn.pack(fill=tk.X, pady=3)
        
        self.stop_btn = self._create_button(
            btn_frame,
            "⏹ Finalizar Suministro",
            self._on_stop_supply,
            self.warning_color
        )
        self.stop_btn.pack(fill=tk.X, pady=3)
        self.stop_btn.config(state=tk.DISABLED)
        
        separator = tk.Frame(card, bg="#45475a", height=1)
        separator.pack(fill=tk.X, padx=15, pady=10)
        
        breakdown_frame = tk.Frame(card, bg=self.card_color)
        breakdown_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.breakdown_btn = self._create_button(
            breakdown_frame,
            "⚠ Simular Avería",
            self._on_breakdown,
            self.error_color
        )
        self.breakdown_btn.pack(fill=tk.X, pady=3)
        
        self.repair_btn = self._create_button(
            breakdown_frame,
            "🔧 Reparar",
            self._on_repair,
            self.accent_color
        )
        self.repair_btn.pack(fill=tk.X, pady=3)
        self.repair_btn.config(state=tk.DISABLED)
        
    def _create_button(self, parent, text, command, color):
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=color,
            fg="#1e1e2e",
            activebackground=color,
            activeforeground="#1e1e2e",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=command
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self._lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
        
    def _lighten_color(self, color):
        return color
        
    def _create_log_card(self, parent):
        card = tk.Frame(parent, bg=self.card_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(
            card,
            text="Registro de Eventos",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_color,
            fg=self.fg_color,
            anchor=tk.W
        )
        title.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        log_frame = tk.Frame(card, bg=self.card_color)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 9),
            bg="#45475a",
            fg=self.fg_color,
            relief=tk.FLAT,
            bd=0,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
    def _on_request_supply(self):
        driver_id = self.driver_entry.get().strip()
        if not driver_id:
            messagebox.showwarning("Advertencia", "Ingrese un ID de conductor")
            return
            
        with self.engine.lock:
            if self.engine.charging:
                messagebox.showerror("Error", "El punto de carga ya está suministrando")
                return
                
        self.log_message(f"Solicitando suministro para: {driver_id}")
        request = {'conductor_id': driver_id, 'cp_id': self.engine.cp_id, 'origen': 'GUI'}
        
        try:
            self.engine.producer.send('solicitudes_suministro', request)
            self.engine.producer.flush()
            self.driver_entry.delete(0, tk.END)
        except Exception as e:
            self.log_message(f"ERROR: No se pudo enviar la solicitud")
            self.engine._reconnect_kafka()
            
    def _on_stop_supply(self):
        with self.engine.lock:
            if self.engine.charging:
                self.engine.charging = False
                self.log_message("Finalizando suministro...")
            else:
                messagebox.showinfo("Info", "No hay suministro activo")
                
    def _on_breakdown(self):
        with self.engine.lock:
            self.engine.breakdown_status = True
        self.log_message("AVERÍA simulada")
        self.breakdown_btn.config(state=tk.DISABLED)
        self.repair_btn.config(state=tk.NORMAL)
        
    def _on_repair(self):
        with self.engine.lock:
            self.engine.breakdown_status = False
        self.log_message("Sistema REPARADO")
        self.breakdown_btn.config(state=tk.NORMAL)
        self.repair_btn.config(state=tk.DISABLED)
        
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def _start_update_loop(self):
        self._update_status()
        
    def _update_status(self):
        if not self.root.winfo_exists():
            return
            
        with self.engine.lock:
            breakdown = self.engine.breakdown_status
            charging = self.engine.charging
            driver = self.engine.current_driver
            
        if breakdown:
            self.status_label.config(text="● AVERÍA", fg=self.error_color)
        elif charging:
            self.status_label.config(text="SUMINISTRANDO", fg=self.warning_color)
        else:
            self.status_label.config(text="OK", fg=self.success_color)
            
        kafka_status = "Conectado" if self.engine.producer else "Desconectado"
        kafka_color = self.success_color if self.engine.producer else self.error_color
        self.kafka_status.config(text=kafka_status, fg=kafka_color)
        
        if charging and driver:
            self.supply_status.config(text=f"Conductor: {driver}")
            self.stop_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.DISABLED)
        else:
            self.supply_status.config(text="Sin suministro activo")
            self.stop_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
            self.consumption_label.config(text="0.00 kWh")
            self.price_current_label.config(text="0.00 EUR")
            self.time_label.config(text="0s")
            
        self.root.after(500, self._update_status)
        
    def _update_metrics(self, consumed_kwh, total_price, duration):
        self.consumption_label.config(text=f"{consumed_kwh:.2f} kWh")
        self.price_current_label.config(text=f"{total_price:.2f} EUR")
        self.time_label.config(text=f"{duration}s")
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        if messagebox.askokcancel("Salir", "¿Desea cerrar el punto de carga?"):
            self.engine.end()
            self.root.destroy()