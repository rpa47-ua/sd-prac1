// Configuración de la API
const API_BASE_URL = 'http://localhost:8000/api';
const REFRESH_INTERVAL = 3000; // 3 segundos

let refreshTimer = null;

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    console.log('Frontend iniciado');

    // Cargar datos iniciales
    loadAllData();

    // Configurar actualización automática
    refreshTimer = setInterval(loadAllData, REFRESH_INTERVAL);

    // Configurar modal
    setupModal();
});

// Cargar todos los datos
async function loadAllData() {
    try {
        await Promise.all([
            loadSystemStatus(),
            loadCPs(),
            loadSupplies(),
            loadWeatherAlerts(),
            loadAudit()
        ]);

        updateConnectionStatus(true);
        updateLastUpdateTime();
    } catch (error) {
        console.error('Error cargando datos:', error);
        updateConnectionStatus(false);
    }
}

// Estado general del sistema
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/status`);
        const data = await response.json();

        if (data.status === 'ok') {
            const stats = data.estadisticas_cps;
            document.getElementById('total-cps').textContent = stats.total;
            document.getElementById('active-cps').textContent = stats.activos;
            document.getElementById('supplying-cps').textContent = stats.suministrando;
            document.getElementById('faulty-cps').textContent = stats.averiados;
            document.getElementById('weather-alerts').textContent = data.cps_con_alerta;
            document.getElementById('active-supplies').textContent = data.suministros_activos;
        }
    } catch (error) {
        console.error('Error cargando estado del sistema:', error);
    }
}

// Cargar lista de CPs
async function loadCPs() {
    try {
        const response = await fetch(`${API_BASE_URL}/cps`);
        const data = await response.json();

        if (data.status === 'ok') {
            const tbody = document.getElementById('cps-tbody');
            tbody.innerHTML = '';

            if (data.cps.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading">No hay CPs registrados</td></tr>';
                return;
            }

            data.cps.forEach(cp => {
                const tr = document.createElement('tr');

                const ubicacion = cp.latitud && cp.longitud
                    ? `${cp.latitud.toFixed(4)}, ${cp.longitud.toFixed(4)}`
                    : 'No disponible';

                const clima = cp.estado_meteorologico || 'Sin datos';
                const alerta = cp.alerta_meteorologica
                    ? '<span class="alert-yes">SÍ</span>'
                    : '<span class="alert-no">NO</span>';

                tr.innerHTML = `
                    <td>${cp.id}</td>
                    <td><span class="status-badge status-${cp.estado}">${cp.estado}</span></td>
                    <td>${clima}</td>
                    <td>${alerta}</td>
                    <td>${ubicacion}</td>
                    <td><button class="btn btn-primary" onclick="showCPDetails('${cp.id}')">Ver Detalles</button></td>
                `;

                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error('Error cargando CPs:', error);
    }
}

// Cargar suministros activos
async function loadSupplies() {
    try {
        const response = await fetch(`${API_BASE_URL}/suministros`);
        const data = await response.json();

        if (data.status === 'ok') {
            const tbody = document.getElementById('supplies-tbody');
            tbody.innerHTML = '';

            if (data.suministros.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="loading">No hay suministros activos</td></tr>';
                return;
            }

            data.suministros.forEach(s => {
                const tr = document.createElement('tr');

                const fechaInicio = new Date(s.fecha_inicio).toLocaleString('es-ES');

                tr.innerHTML = `
                    <td>${s.id}</td>
                    <td>${s.conductor_id}</td>
                    <td>${s.cp_id}</td>
                    <td>${fechaInicio}</td>
                    <td>${s.consumo_kwh.toFixed(3)}</td>
                    <td>${s.importe_total.toFixed(2)}</td>
                    <td><span class="status-badge status-${s.estado}">${s.estado}</span></td>
                `;

                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error('Error cargando suministros:', error);
    }
}

// Cargar alertas meteorológicas
async function loadWeatherAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/weather/alerts`);
        const data = await response.json();

        if (data.status === 'ok') {
            const container = document.getElementById('weather-alerts-container');
            container.innerHTML = '';

            if (data.alertas.length === 0) {
                container.innerHTML = '<p class="loading">No hay alertas meteorológicas activas</p>';
                return;
            }

            data.alertas.forEach(alerta => {
                const card = document.createElement('div');
                card.className = 'alert-card critical';

                const ubicacion = alerta.latitud && alerta.longitud
                    ? `${alerta.latitud.toFixed(4)}, ${alerta.longitud.toFixed(4)}`
                    : 'No disponible';

                card.innerHTML = `
                    <h3>⚠️ ${alerta.cp_id}</h3>
                    <p><strong>Estado:</strong> ${alerta.estado}</p>
                    <p><strong>Clima:</strong> ${alerta.estado_meteorologico || 'Sin datos'}</p>
                    <p><strong>Ubicación:</strong> ${ubicacion}</p>
                `;

                container.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error cargando alertas meteorológicas:', error);
    }
}

// Cargar auditoría
async function loadAudit() {
    try {
        const response = await fetch(`${API_BASE_URL}/auditoria?limit=50`);
        const data = await response.json();

        if (data.status === 'ok') {
            const tbody = document.getElementById('audit-tbody');
            tbody.innerHTML = '';

            if (data.registros.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="loading">No hay registros de auditoría</td></tr>';
                return;
            }

            data.registros.forEach(r => {
                const tr = document.createElement('tr');

                const timestamp = new Date(r.timestamp).toLocaleString('es-ES');
                const resultadoClass = r.resultado === 'exito' ? 'alert-no' : 'alert-yes';

                tr.innerHTML = `
                    <td>${timestamp}</td>
                    <td>${r.modulo}</td>
                    <td>${r.accion}</td>
                    <td>${r.ip_origen || 'N/A'}</td>
                    <td><span class="${resultadoClass}">${r.resultado}</span></td>
                `;

                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error('Error cargando auditoría:', error);
    }
}

// Mostrar detalles de un CP
async function showCPDetails(cpId) {
    try {
        const response = await fetch(`${API_BASE_URL}/cps/${cpId}`);
        const data = await response.json();

        if (data.status === 'ok') {
            const cp = data.cp;
            const detailsDiv = document.getElementById('cp-details');

            let suministroInfo = '<p>Sin suministro activo</p>';
            if (cp.suministro_activo) {
                const s = cp.suministro_activo;
                const fechaInicio = new Date(s.fecha_inicio).toLocaleString('es-ES');
                suministroInfo = `
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        <h3>Suministro Activo</h3>
                        <p><strong>ID Suministro:</strong> ${s.id}</p>
                        <p><strong>Conductor:</strong> ${s.conductor_id}</p>
                        <p><strong>Inicio:</strong> ${fechaInicio}</p>
                        <p><strong>Consumo:</strong> ${s.consumo_kwh.toFixed(3)} kWh</p>
                        <p><strong>Importe:</strong> ${s.importe_total.toFixed(2)} €</p>
                    </div>
                `;
            }

            const ubicacion = cp.latitud && cp.longitud
                ? `${cp.latitud.toFixed(6)}, ${cp.longitud.toFixed(6)}`
                : 'No configurada';

            detailsDiv.innerHTML = `
                <p><strong>ID:</strong> ${cp.id}</p>
                <p><strong>Estado:</strong> <span class="status-badge status-${cp.estado}">${cp.estado}</span></p>
                <p><strong>Fecha Registro:</strong> ${new Date(cp.fecha_registro).toLocaleString('es-ES')}</p>
                <p><strong>Ubicación GPS:</strong> ${ubicacion}</p>
                <p><strong>Estado Meteorológico:</strong> ${cp.estado_meteorologico || 'Sin datos'}</p>
                <p><strong>Alerta Meteorológica:</strong> ${cp.alerta_meteorologica ? 'SÍ' : 'NO'}</p>
                ${suministroInfo}
            `;

            document.getElementById('cp-modal').style.display = 'block';
        }
    } catch (error) {
        console.error('Error cargando detalles del CP:', error);
        alert('Error al cargar los detalles del CP');
    }
}

// Configurar modal
function setupModal() {
    const modal = document.getElementById('cp-modal');
    const closeBtn = document.querySelector('.close');

    closeBtn.onclick = () => {
        modal.style.display = 'none';
    };

    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// Actualizar estado de conexión
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = 'Conectado';
        statusEl.className = 'status-connected';
    } else {
        statusEl.textContent = 'Desconectado';
        statusEl.className = 'status-disconnected';
    }
}

// Actualizar timestamp de última actualización
function updateLastUpdateTime() {
    const now = new Date().toLocaleTimeString('es-ES');
    document.getElementById('last-update').textContent = now;
}