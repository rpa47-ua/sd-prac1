import tkinter as tk
from tkinter import ttk
import time

class EVDriverGUI:
    def __init__(self, driver):
        self.driver = driver
        self.root = tk.Tk()
        self.root.title(f"Sistema de Conductor - {driver.driver_id}")
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
            text="🚗",
            font=("Segoe UI", 32),
            bg=self.bg_medium,
            fg=self.accent_cyan
        )
        logo_text.pack()
        
        title = tk.Label(
            logo_frame,
            text="EV Driver",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_medium,
            fg=self.text_primary
        )
        title.pack(pady=(5, 0))
        
        subtitle = tk.Label(
            logo_frame,
            text=self.driver.driver_id,
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
            text="Estado",
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
            text="DISPONIBLE",
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
        self._create_sidebar_info(parent, "CP Actual", "---", "current_cp_status")
        
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
            text="Panel de Conductor",
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
        
        self._create_charging_control_card(left_panel)

        right_panel = tk.Frame(bottom_row, bg=self.bg_dark)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self._create_cp_list_card(right_panel)
        
    def _create_metric_cards(self, parent):
        metrics = [
            ("Consumo", "0.00", "kWh", "consumption_metric", self.accent_cyan),
            ("Importe", "0.00", "EUR", "price_metric", self.accent_blue),
            ("Tiempo", "0", "seg", "time_metric", self.accent_purple),
            ("Estado", "Disponible", "", "status_metric", self.success)
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
        elif label == "Estado":
            self.status_value = value_label
            
        return card
        
    def _create_charging_control_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card)
        card.pack(fill=tk.BOTH, expand=True)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        tk.Label(
            content,
            text="Solicitar Carga",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(anchor=tk.W)
        
        tk.Label(
            content,
            text="Seleccione o ingrese el ID del punto de carga",
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
            text="Carga Actual",
            font=("Segoe UI", 9),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)
        
        self.current_charging_label = tk.Label(
            info_content,
            text="Sin carga activa",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.text_secondary
        )
        self.current_charging_label.pack(anchor=tk.W, pady=(5, 0))

        tk.Label(
            content,
            text="ID del Punto de Carga",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary
        ).pack(anchor=tk.W, pady=(0, 8))
        
        self.cp_entry = tk.Entry(
            content,
            font=("Segoe UI", 12),
            bg=self.bg_light,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0
        )
        self.cp_entry.pack(fill=tk.X, ipady=12, ipadx=15)

        button_frame = tk.Frame(content, bg=self.bg_card)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.request_btn = self._create_gradient_button(
            button_frame,
            "Solicitar Carga",
            self._on_request_charging,
            self.accent_blue,
            self.accent_cyan
        )
        self.request_btn.pack(fill=tk.X)
        
    def _create_cp_list_card(self, parent):
        card = tk.Frame(parent, bg=self.bg_card)
        card.pack(fill=tk.BOTH, expand=True)
        
        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        title_frame = tk.Frame(content, bg=self.bg_card)
        title_frame.pack(fill=tk.X)
        
        tk.Label(
            title_frame,
            text="Puntos de Carga Disponibles",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(side=tk.LEFT)
        
        refresh_btn = tk.Button(
            title_frame,
            text="⟳",
            font=("Segoe UI", 16),
            bg=self.bg_light,
            fg=self.accent_blue,
            activebackground=self.bg_light,
            activeforeground=self.accent_cyan,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._on_refresh_cp_list,
            width=3
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        tk.Label(
            content,
            text="Haga clic en un punto de carga para solicitar",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_dim
        ).pack(anchor=tk.W, pady=(5, 15))

        list_container = tk.Frame(content, bg=self.bg_card)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.cp_canvas = tk.Canvas(
            list_container,
            bg=self.bg_card,
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.cp_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.cp_canvas.yview)

        self.cp_list_frame = tk.Frame(self.cp_canvas, bg=self.bg_card)
        self.cp_canvas_window = self.cp_canvas.create_window(
            (0, 0),
            window=self.cp_list_frame,
            anchor=tk.NW
        )

        self.cp_list_frame.bind("<Configure>", self._on_cp_list_configure)
        self.cp_canvas.bind("<Configure>", self._on_canvas_configure)
        
    def _on_cp_list_configure(self, event):
        self.cp_canvas.configure(scrollregion=self.cp_canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        self.cp_canvas.itemconfig(self.cp_canvas_window, width=event.width)
        
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
        
    def _on_request_charging(self):
        cp_id = self.cp_entry.get().strip().upper()
        if not cp_id:
            return
            
        with self.driver.lock:
            if self.driver.charging:
                return

        self.driver._send_charging_request(cp_id)
        
    def _on_refresh_cp_list(self):
        self.driver._request_cp_list()
        
    def _update_cp_list(self):
        for widget in self.cp_list_frame.winfo_children():
            widget.destroy()
        
        with self.driver.lock:
            cp_list = dict(self.driver.cp_list)
        
        if not cp_list:
            tk.Label(
                self.cp_list_frame,
                text="No hay puntos de carga disponibles",
                font=("Segoe UI", 11),
                bg=self.bg_card,
                fg=self.text_dim
            ).pack(pady=20)
            return
        
        for cp_id, estado in sorted(cp_list.items()):
            self._create_cp_item(cp_id, estado)
            
    def _create_cp_item(self, cp_id, estado):
        item = tk.Frame(self.cp_list_frame, bg=self.bg_light, cursor="hand2")
        item.pack(fill=tk.X, pady=(0, 8))
        
        content = tk.Frame(item, bg=self.bg_light)
        content.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            content,
            text=cp_id,
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_light,
            fg=self.text_primary
        ).pack(side=tk.LEFT)

        if estado == 'activado':
            status_text = "Disponible"
            status_color = self.success
        elif estado == 'suministrando':
            status_text = "Suministrando"
            status_color = self.warning
        elif estado == 'averiado':
            status_text = "Averiado"
            status_color = self.error
        elif estado == 'parado':
            status_text = "Parado"
            status_color = self.text_dim
        else:
            status_text = estado.capitalize()
            status_color = self.text_secondary
        
        status_label = tk.Label(
            content,
            text=status_text,
            font=("Segoe UI", 10),
            bg=self.bg_light,
            fg=status_color
        )
        status_label.pack(side=tk.RIGHT)

        item.bind("<Button-1>", lambda e: self._on_cp_item_click(cp_id, estado))
        for child in item.winfo_children():
            child.bind("<Button-1>", lambda e: self._on_cp_item_click(cp_id, estado))
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", lambda e: self._on_cp_item_click(cp_id, estado))
        
    def _on_cp_item_click(self, cp_id, estado):
        if estado == 'activado':
            self.cp_entry.delete(0, tk.END)
            self.cp_entry.insert(0, cp_id)
            self._on_request_charging()
            
    def _start_update_loop(self):
        self._update_status()
        self._update_cp_list()
        
    def _update_status(self):
        try:
            if not self.root.winfo_exists():
                return
        except:
            return
            
        with self.driver.lock:
            charging = self.driver.charging
            current_cp = self.driver.current_cp
            consumption = self.driver.current_consumption
            price = self.driver.current_price

        if charging:
            self.status_indicator.config(fg=self.warning)
            self.status_text.config(text="CARGANDO")
            self.status_value.config(text="Cargando", fg=self.warning)
        else:
            self.status_indicator.config(fg=self.success)
            self.status_text.config(text="DISPONIBLE")
            self.status_value.config(text="Disponible", fg=self.success)

        kafka_text = "Conectado" if self.driver.producer else "Desconectado"
        kafka_color = self.success if self.driver.producer else self.error
        self.kafka_status.config(text=kafka_text, fg=kafka_color)

        if current_cp:
            self.current_cp_status.config(text=current_cp, fg=self.text_primary)
        else:
            self.current_cp_status.config(text="---", fg=self.text_dim)

        if charging and current_cp:
            self.current_charging_label.config(text=f"Cargando en: {current_cp}", fg=self.text_primary)
            self.cp_entry.config(state=tk.DISABLED, disabledbackground=self.bg_light, disabledforeground=self.text_dim)
            self.request_btn.config(state=tk.DISABLED, bg=self.border)
            
            self.consumption_value.config(text=f"{consumption:.2f}")
            self.price_value.config(text=f"{price:.2f}")
        else:
            self.current_charging_label.config(text="Sin carga activa", fg=self.text_dim)
            self.cp_entry.config(state=tk.NORMAL, bg=self.bg_light)
            if self.driver.producer:
                self.request_btn.config(state=tk.NORMAL, bg=self.accent_blue)
            else:
                self.request_btn.config(state=tk.DISABLED, bg=self.border)
            
            self.consumption_value.config(text="0.00")
            self.price_value.config(text="0.00")
            self.time_value.config(text="0")
        
        try:
            self.root.after(500, self._update_status)
        except:
            pass
            
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(1000, self._on_refresh_cp_list)
        self.root.after(1500, self._update_cp_list)
        try:
            self.root.mainloop()
        except:
            pass
        
    def _on_close(self):
        try:
            self.root.destroy()
        except:
            pass
        self.driver.gui = None