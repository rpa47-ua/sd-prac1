"""
Panel de monitorización GUI para EV_Central usando Tkinter
Interfaz visual moderna y profesional
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import time


class PanelGUI:
    def __init__(self, logica_negocio):
        self.logica = logica_negocio
        self.running = False
        self.root = None
        self.tree = None
        self.stats_labels = {}

        # Colores del tema
        self.COLORS = {
            'activado': '#4CAF50',      # Verde
            'parado': '#FF9800',         # Naranja
            'suministrando': '#2196F3',  # Azul
            'averiado': '#F44336',       # Rojo
            'desconectado': '#9E9E9E',   # Gris
            'bg_main': '#1E1E1E',        # Fondo oscuro
            'bg_panel': '#2D2D2D',       # Fondo panel
            'text': '#FFFFFF',           # Texto blanco
            'accent': '#00BCD4'          # Acento cyan
        }

    def iniciar(self):
        """Inicia la interfaz gráfica en el hilo principal"""
        self.running = True
        self.root = tk.Tk()
        self.root.title("🔋 EV CHARGING - Panel de Monitorización Central")
        self.root.geometry("1200x700")
        self.root.configure(bg=self.COLORS['bg_main'])

        self._crear_interfaz()

        # Actualizar datos cada 2 segundos
        self._actualizar_datos()

        print("✓ Panel GUI iniciado")

        # Iniciar el mainloop
        self.root.mainloop()

    def _crear_interfaz(self):
        """Crea todos los elementos de la interfaz"""

        # ==================== ENCABEZADO ====================
        header_frame = tk.Frame(self.root, bg=self.COLORS['accent'], height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="🔋 EV CHARGING NETWORK",
            font=("Arial", 24, "bold"),
            bg=self.COLORS['accent'],
            fg=self.COLORS['text']
        )
        title_label.pack(pady=20)

        # ==================== ESTADÍSTICAS ====================
        stats_frame = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        stats_frame.pack(fill=tk.X, padx=20, pady=10)

        self.time_label = tk.Label(
            stats_frame,
            text="",
            font=("Arial", 12),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text']
        )
        self.time_label.pack(side=tk.LEFT, padx=10)

        # Contenedor de estadísticas
        stats_container = tk.Frame(stats_frame, bg=self.COLORS['bg_main'])
        stats_container.pack(side=tk.RIGHT)

        stats_info = [
            ('total', 'Total CPs', self.COLORS['text']),
            ('activados', 'Disponibles', self.COLORS['activado']),
            ('suministrando', 'Suministrando', self.COLORS['suministrando']),
            ('averiados', 'Averiados', self.COLORS['averiado'])
        ]

        for key, label, color in stats_info:
            frame = tk.Frame(stats_container, bg=self.COLORS['bg_panel'], relief=tk.RAISED, bd=2)
            frame.pack(side=tk.LEFT, padx=5)

            tk.Label(
                frame,
                text=label,
                font=("Arial", 9),
                bg=self.COLORS['bg_panel'],
                fg=self.COLORS['text']
            ).pack(padx=10, pady=(5, 0))

            value_label = tk.Label(
                frame,
                text="0",
                font=("Arial", 20, "bold"),
                bg=self.COLORS['bg_panel'],
                fg=color
            )
            value_label.pack(padx=10, pady=(0, 5))

            self.stats_labels[key] = value_label

        # ==================== TABLA DE CHARGING POINTS ====================
        table_frame = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(
            table_frame,
            text="CHARGING POINTS",
            font=("Arial", 14, "bold"),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text']
        ).pack(anchor=tk.W, pady=(0, 10))

        # Crear Treeview
        columns = ('ID', 'Ubicación', 'Estado', 'Precio €/kWh', 'Conductor', 'Consumo kWh', 'Importe €')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Ubicación', text='Ubicación')
        self.tree.heading('Estado', text='Estado')
        self.tree.heading('Precio €/kWh', text='Precio €/kWh')
        self.tree.heading('Conductor', text='Conductor')
        self.tree.heading('Consumo kWh', text='Consumo kWh')
        self.tree.heading('Importe €', text='Importe €')

        self.tree.column('ID', width=80, anchor=tk.CENTER)
        self.tree.column('Ubicación', width=250, anchor=tk.W)
        self.tree.column('Estado', width=150, anchor=tk.CENTER)
        self.tree.column('Precio €/kWh', width=120, anchor=tk.CENTER)
        self.tree.column('Conductor', width=100, anchor=tk.CENTER)
        self.tree.column('Consumo kWh', width=120, anchor=tk.CENTER)
        self.tree.column('Importe €', width=100, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Estilo de la tabla
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                       background=self.COLORS['bg_panel'],
                       foreground=self.COLORS['text'],
                       fieldbackground=self.COLORS['bg_panel'],
                       borderwidth=0,
                       font=('Arial', 10))
        style.configure('Treeview.Heading',
                       background=self.COLORS['accent'],
                       foreground=self.COLORS['text'],
                       font=('Arial', 11, 'bold'))
        style.map('Treeview', background=[('selected', self.COLORS['accent'])])

        # ==================== BOTONES DE CONTROL ====================
        control_frame = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(
            control_frame,
            text="CONTROL DE CPs",
            font=("Arial", 12, "bold"),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text']
        ).pack(side=tk.LEFT, padx=(0, 20))

        btn_style = {
            'font': ('Arial', 11, 'bold'),
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 10
        }

        tk.Button(
            control_frame,
            text="🛑 Parar CP Seleccionado",
            bg=self.COLORS['parado'],
            fg=self.COLORS['text'],
            command=self._parar_cp,
            **btn_style
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            control_frame,
            text="▶️ Reanudar CP Seleccionado",
            bg=self.COLORS['activado'],
            fg=self.COLORS['text'],
            command=self._reanudar_cp,
            **btn_style
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            control_frame,
            text="🔄 Actualizar",
            bg=self.COLORS['accent'],
            fg=self.COLORS['text'],
            command=self._actualizar_manual,
            **btn_style
        ).pack(side=tk.LEFT, padx=5)

    def _actualizar_datos(self):
        """Actualiza los datos del panel periódicamente"""
        if not self.running:
            return

        try:
            # Guardar selección actual
            selected_items = self.tree.selection()
            selected_cp_id = None
            if selected_items:
                item = self.tree.item(selected_items[0])
                selected_cp_id = item['values'][0] if item['values'] else None

            # Obtener estado del sistema
            estado = self.logica.obtener_estado_sistema()
            cps = estado['cps']
            suministros = estado['suministros_activos']

            # Actualizar hora
            self.time_label.config(text=f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Actualizar estadísticas
            total = len(cps)
            activados = len([cp for cp in cps if cp['estado'] == 'activado'])
            suministrando = len([cp for cp in cps if cp['estado'] == 'suministrando'])
            averiados = len([cp for cp in cps if cp['estado'] == 'averiado'])

            self.stats_labels['total'].config(text=str(total))
            self.stats_labels['activados'].config(text=str(activados))
            self.stats_labels['suministrando'].config(text=str(suministrando))
            self.stats_labels['averiados'].config(text=str(averiados))

            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Llenar tabla
            for cp in cps:
                cp_id = cp['id']
                ubicacion = cp['ubicacion']
                estado_raw = cp['estado']
                estado = estado_raw.upper()
                precio = f"{cp['precio_kwh']:.3f}"

                conductor = '-'
                consumo = '-'
                importe = '-'

                # Si está en estado parado, mostrar "Out of Order"
                if estado_raw == 'parado':
                    estado = "OUT OF ORDER"

                # Si está suministrando, mostrar detalles
                if cp_id in suministros:
                    info = suministros[cp_id]
                    conductor = info['conductor_id']
                    consumo = f"{info['consumo_actual']:.2f} kWh"
                    importe = f"{info['importe_actual']:.2f} €"

                # Insertar fila con color según estado
                item = self.tree.insert('', tk.END, values=(cp_id, ubicacion, estado, precio, conductor, consumo, importe))

                # Aplicar color (tags)
                self.tree.item(item, tags=(estado_raw,))

            # Configurar colores de filas
            for estado, color in self.COLORS.items():
                if estado not in ['bg_main', 'bg_panel', 'text', 'accent']:
                    self.tree.tag_configure(estado, background=color, foreground='white')

            # Restaurar selección si existía
            if selected_cp_id:
                for item in self.tree.get_children():
                    item_values = self.tree.item(item)['values']
                    if item_values and item_values[0] == selected_cp_id:
                        self.tree.selection_set(item)
                        self.tree.see(item)  # Hacer scroll si es necesario
                        break

        except Exception as e:
            print(f"Error actualizando panel: {e}")

        # Programar siguiente actualización
        if self.running:
            self.root.after(2000, self._actualizar_datos)

    def _actualizar_manual(self):
        """Actualización manual (botón)"""
        self._actualizar_datos()

    def _parar_cp(self):
        """Para el CP seleccionado"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selección", "Por favor selecciona un Charging Point")
            return

        item = self.tree.item(selected[0])
        cp_id = item['values'][0]
        estado = item['values'][2]

        # Validaciones rápidas
        if estado == 'DESCONECTADO':
            messagebox.showerror("Error", f"CP {cp_id} desconectado")
            return

        if estado == 'OUT OF ORDER':
            messagebox.showinfo("Info", f"CP {cp_id} ya está parado")
            return

        if estado == 'AVERIADO':
            messagebox.showerror("Error", f"CP {cp_id} averiado")
            return

        # Confirmación simple
        if messagebox.askyesno("Confirmar", f"¿Parar CP {cp_id}?"):
            self.logica.parar_cp(cp_id)
            self._actualizar_datos()

    def _reanudar_cp(self):
        """Reanuda el CP seleccionado"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selección", "Por favor selecciona un Charging Point")
            return

        item = self.tree.item(selected[0])
        cp_id = item['values'][0]
        estado = item['values'][2]

        # Validaciones rápidas
        if estado == 'DESCONECTADO':
            messagebox.showerror("Error", f"CP {cp_id} desconectado")
            return

        if estado == 'ACTIVADO':
            messagebox.showinfo("Info", f"CP {cp_id} ya está activo")
            return

        if estado == 'SUMINISTRANDO':
            messagebox.showinfo("Info", f"CP {cp_id} suministrando")
            return

        if estado == 'AVERIADO':
            messagebox.showerror("Error", f"CP {cp_id} averiado")
            return

        # Confirmación simple
        if messagebox.askyesno("Confirmar", f"¿Reanudar CP {cp_id}?"):
            self.logica.reanudar_cp(cp_id)
            self._actualizar_datos()

    def detener(self):
        """Detiene el panel GUI"""
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
        print("✓ Panel GUI detenido")