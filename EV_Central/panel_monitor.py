"""
Panel de monitorización visual para EV_Central
Muestra el estado de todos los CPs en tiempo real
"""
import os
import time
from datetime import datetime


class PanelMonitor:
    def __init__(self, logica_negocio):
        self.logica = logica_negocio
        self.running = False

        # Colores ANSI para terminal
        self.COLORS = {
            'activado': '\033[92m',      # Verde
            'parado': '\033[93m',         # Amarillo/Naranja
            'suministrando': '\033[96m',  # Cyan
            'averiado': '\033[91m',       # Rojo
            'desconectado': '\033[90m',   # Gris
            'RESET': '\033[0m',
            'BOLD': '\033[1m'
        }

    def iniciar(self):
        """Inicia el panel de monitorización"""
        self.running = True
        print("✓ Panel de monitorización iniciado")

    def mostrar(self):
        """Muestra el estado actual del sistema en consola"""
        if not self.running:
            return

        # Limpiar pantalla (multiplataforma)
        os.system('cls' if os.name == 'nt' else 'clear')

        # Obtener estado del sistema
        estado = self.logica.obtener_estado_sistema()
        cps = estado['cps']
        suministros = estado['suministros_activos']

        # Encabezado
        print(self._color('BOLD') + "=" * 80)
        print("🔋 EV CHARGING - PANEL DE MONITORIZACIÓN CENTRAL")
        print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + self._color('RESET'))
        print()

        # Tabla de CPs
        print(self._color('BOLD') + "CHARGING POINTS:" + self._color('RESET'))
        print("-" * 80)
        print(f"{'ID':<10} {'Ubicación':<30} {'Estado':<15} {'Precio €/kWh':<12}")
        print("-" * 80)

        for cp in cps:
            cp_id = cp['id']
            ubicacion = cp['ubicacion']
            estado = cp['estado']
            precio = cp['precio_kwh']

            color = self.COLORS.get(estado, '')
            reset = self.COLORS['RESET']

            estado_display = f"{color}{estado.upper()}{reset}"

            print(f"{cp_id:<10} {ubicacion:<30} {estado_display:<24} {precio:<12.3f}")

            # Si está suministrando, mostrar detalles
            if cp_id in suministros:
                info = suministros[cp_id]
                print(f"           → Conductor: {info['conductor_id']} | "
                      f"Consumo: {info['consumo_actual']:.2f} kWh | "
                      f"Importe: {info['importe_actual']:.2f} €")

        print("-" * 80)
        print()

        # Resumen
        total_cps = len(cps)
        activados = len([cp for cp in cps if cp['estado'] == 'activado'])
        suministrando = len([cp for cp in cps if cp['estado'] == 'suministrando'])
        averiados = len([cp for cp in cps if cp['estado'] == 'averiado'])

        print(f"📊 Total CPs: {total_cps} | "
              f"{self.COLORS['activado']}Disponibles: {activados}{self.COLORS['RESET']} | "
              f"{self.COLORS['suministrando']}Suministrando: {suministrando}{self.COLORS['RESET']} | "
              f"{self.COLORS['averiado']}Averiados: {averiados}{self.COLORS['RESET']}")
        print()

        print("Comandos: (p)arar CP | (r)eanudar CP | (q)uit")

    def _color(self, nombre):
        """Retorna código de color ANSI"""
        return self.COLORS.get(nombre, '')

    def detener(self):
        """Detiene el panel"""
        self.running = False
        print("✓ Panel de monitorización detenido")
