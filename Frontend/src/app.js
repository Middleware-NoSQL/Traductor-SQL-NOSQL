// Configuración de la API
const API_URL = 'http://localhost:5000';
let queryCount = 0;

// Elementos del DOM
const databaseSelect = document.getElementById('database-select');
const collectionSelect = document.getElementById('collection-select');
const sqlQuery = document.getElementById('sql-query');
const executeBtn = document.getElementById('execute-btn');
const clearBtn = document.getElementById('clear-btn');
const mongoQueryDisplay = document.getElementById('mongo-query-display');
const resultsTable = document.getElementById('results-table');
const resultsCount = document.getElementById('results-count');
const dbCount = document.getElementById('db-count');
const collectionsCount = document.getElementById('collections-count');
const queriesCount = document.getElementById('queries-count');
const loader = document.getElementById('loader');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');
const toastIcon = document.getElementById('toast-icon');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');
const rawQueryDisplay = document.getElementById('raw-query-display');

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    loadDatabases();
    setupEventListeners();
});

// Cargar bases de datos disponibles
async function loadDatabases() {
    showLoader();
    try {
        const response = await fetch(`${API_URL}/databases`);
        const data = await response.json();
        
        if (data.error) {
            showToast('error', data.error);
            return;
        }
        
        const databases = data.databases || [];
        dbCount.textContent = databases.length;
        
        // Limpiar select
        databaseSelect.innerHTML = '<option value="">Seleccionar base de datos...</option>';
        
        // Añadir opciones
        databases.forEach(db => {
            const option = document.createElement('option');
            option.value = db;
            option.textContent = db;
            databaseSelect.appendChild(option);
        });
        
    } catch (error) {
        showToast('error', 'Error al cargar bases de datos');
        console.error('Error:', error);
    } finally {
        hideLoader();
    }
}

// Cargar colecciones de una base de datos
async function loadCollections(databaseName) {
    showLoader();
    try {
        const response = await fetch(`${API_URL}/database/${databaseName}/collections`);
        const data = await response.json();
        
        if (data.error) {
            showToast('error', data.error);
            return;
        }
        
        const collections = data.collections || [];
        collectionsCount.textContent = collections.length;
        
        // Limpiar select
        collectionSelect.innerHTML = '<option value="">Seleccionar colección...</option>';
        
        // Añadir opciones
        collections.forEach(collection => {
            const option = document.createElement('option');
            option.value = collection;
            option.textContent = collection;
            collectionSelect.appendChild(option);
        });
        
    } catch (error) {
        showToast('error', 'Error al cargar colecciones');
        console.error('Error:', error);
    } finally {
        hideLoader();
    }
}

// Conectar a una base de datos
async function connectToDatabase(databaseName) {
    showLoader();
    try {
        const response = await fetch(`${API_URL}/connect`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ database: databaseName })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast('error', data.error);
            return false;
        }
        
        showToast('success', `Conectado a ${databaseName}`);
        return true;
        
    } catch (error) {
        showToast('error', 'Error al conectar a la base de datos');
        console.error('Error:', error);
        return false;
    } finally {
        hideLoader();
    }
}

// Ejecutar consulta SQL
async function executeQuery() {
    const sql = sqlQuery.value.trim();
    const database = databaseSelect.value;
    
    if (!sql) {
        showToast('info', 'Ingrese una consulta SQL');
        return;
    }
    
    if (!database) {
        showToast('info', 'Seleccione una base de datos');
        return;
    }
    
    showLoader();
    
    try {
        // Conectar a la base de datos (opcional, ya que el endpoint translate también puede manejar esto)
        await connectToDatabase(database);
        
        // 1. Ejecutar la consulta normal
        const response = await fetch(`${API_URL}/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: sql,
                database: database
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast('error', data.error);
            return;
        }
        
        // Incrementar contador de consultas
        queryCount++;
        queriesCount.textContent = queryCount;
        
        // Mostrar la consulta MongoDB
        displayMongoQuery(data);
        
        // Mostrar resultados
        displayResults(data);
        
        // 2. Obtener y mostrar la consulta para shell de MongoDB
        await generateShellQuery(sql, database);
        
        // Cambiar a la pestaña de consulta MongoDB
        activateTab('mongodb-query');
        
        showToast('success', 'Consulta ejecutada correctamente');
        
    } catch (error) {
        showToast('error', 'Error al ejecutar la consulta');
        console.error('Error:', error);
    } finally {
        hideLoader();
    }
}

// Nueva función para generar la consulta de shell MongoDB
async function generateShellQuery(sql, database) {
    try {
        const response = await fetch(`${API_URL}/generate-shell-query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: sql,
                database: database
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            console.error('Error al generar consulta shell:', data.error);
            rawQueryDisplay.textContent = `// Error: ${data.error}`;
            return;
        }
        
        // Mostrar la consulta shell con resaltado de sintaxis básico
        displayShellQuery(data.shell_query);
        
    } catch (error) {
        console.error('Error al generar consulta shell:', error);
        rawQueryDisplay.textContent = '// Error al generar la consulta para la shell de MongoDB';
    }
}

// Función para mostrar la consulta shell con resaltado básico
function displayShellQuery(shellQuery) {
    if (!shellQuery) {
        rawQueryDisplay.textContent = '// No se pudo generar la consulta para la shell de MongoDB';
        return;
    }
    
    // Añadir botón de copiar si no existe
    const tabPane = document.getElementById('raw-query');
    if (!tabPane.querySelector('.copy-btn')) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copiar';
        copyBtn.style.position = 'absolute';
        copyBtn.style.top = '10px';
        copyBtn.style.right = '10px';
        
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(shellQuery).then(() => {
                showToast('success', 'Consulta copiada al portapapeles');
                
                // Cambiar texto del botón brevemente
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copiar';
                }, 2000);
            });
        });
        
        tabPane.querySelector('.code-container').style.position = 'relative';
        tabPane.querySelector('.code-container').appendChild(copyBtn);
    }
    
    // Convertir caracteres especiales HTML
    let safeQuery = shellQuery
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Crear un array con partes de la cadena para procesar
    let parts = [];
    let currentPart = '';
    let inString = false;
    let quoteChar = '';
    
    // Analizar la cadena carácter por carácter
    for (let i = 0; i < safeQuery.length; i++) {
        const char = safeQuery[i];
        
        // Manejar inicio/fin de strings
        if ((char === '"' || char === "'") && (i === 0 || safeQuery[i - 1] !== '\\')) {
            if (!inString) {
                // Inicio de string
                if (currentPart) {
                    parts.push({ type: 'text', content: currentPart });
                    currentPart = '';
                }
                inString = true;
                quoteChar = char;
                currentPart += char;
            } else if (char === quoteChar) {
                // Fin de string
                currentPart += char;
                parts.push({ type: 'string', content: currentPart });
                currentPart = '';
                inString = false;
            } else {
                // Otro tipo de comilla dentro de un string
                currentPart += char;
            }
        } else if (inString) {
            // Estamos dentro de un string, añadir el carácter al string actual
            currentPart += char;
        } else if (char === '$' && /[a-zA-Z]/.test(safeQuery[i + 1])) {
            // Operador MongoDB (como $eq, $gt, etc.)
            if (currentPart) {
                parts.push({ type: 'text', content: currentPart });
                currentPart = '';
            }
            
            // Capturar todo el operador
            let operator = char;
            let j = i + 1;
            while (j < safeQuery.length && /[a-zA-Z]/.test(safeQuery[j])) {
                operator += safeQuery[j];
                j++;
            }
            
            parts.push({ type: 'operator', content: operator });
            i = j - 1; // Ajustar el índice
        } else if (/[a-zA-Z]/.test(char) && (i === 0 || !/[a-zA-Z0-9_]/.test(safeQuery[i - 1]))) {
            // Posible palabra clave
            if (currentPart) {
                parts.push({ type: 'text', content: currentPart });
                currentPart = '';
            }
            
            // Capturar toda la palabra
            let word = char;
            let j = i + 1;
            while (j < safeQuery.length && /[a-zA-Z0-9_]/.test(safeQuery[j])) {
                word += safeQuery[j];
                j++;
            }
            
            // Verificar si es una palabra clave
            const keywords = ['db', 'find', 'aggregate', 'insertOne', 'updateMany', 'deleteMany', 'pretty', 'sort', 'limit'];
            if (keywords.includes(word)) {
                parts.push({ type: 'keyword', content: word });
            } else {
                parts.push({ type: 'text', content: word });
            }
            
            i = j - 1; // Ajustar el índice
        } else {
            // Cualquier otro carácter
            currentPart += char;
        }
    }
    
    // Añadir la última parte si queda algo
    if (currentPart) {
        parts.push({ type: 'text', content: currentPart });
    }
    
    // Construir HTML con el resaltado
    let highlightedQuery = '';
    for (const part of parts) {
        if (part.type === 'string') {
            highlightedQuery += `<span class="string">${part.content}</span>`;
        } else if (part.type === 'keyword') {
            highlightedQuery += `<span class="keyword">${part.content}</span>`;
        } else if (part.type === 'operator') {
            highlightedQuery += `<span class="function">${part.content}</span>`;
        } else {
            highlightedQuery += part.content;
        }
    }
    
    // Preservar saltos de línea
    highlightedQuery = highlightedQuery.replace(/\n/g, '<br>');
    
    // Establecer el HTML con resaltado
    rawQueryDisplay.innerHTML = highlightedQuery;
}

// Mostrar consulta MongoDB
function displayMongoQuery(data) {
    // Formatear la consulta para mostrarla mejor
    const formattedQuery = JSON.stringify(data, null, 2);
    mongoQueryDisplay.textContent = formattedQuery;
}

// Mostrar resultados en tabla
function displayResults(data) {
    // Limpiar tabla
    const thead = resultsTable.querySelector('thead');
    const tbody = resultsTable.querySelector('tbody');
    
    thead.innerHTML = '<tr><th>#</th><th>_id</th></tr>';
    tbody.innerHTML = '';
    
    // Si es un array, asumir que son resultados de SELECT/FIND
    if (Array.isArray(data)) {
        if (data.length === 0) {
            resultsCount.textContent = '0 resultados encontrados';
            return;
        }
        
        resultsCount.textContent = `${data.length} resultados encontrados`;
        
        // Obtener todas las claves únicas para las columnas
        const allKeys = new Set();
        data.forEach(item => {
            Object.keys(item).forEach(key => {
                if (key !== '_id') {
                    allKeys.add(key);
                }
            });
        });
        
        // Añadir encabezados
        const headerRow = thead.querySelector('tr');
        allKeys.forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            headerRow.appendChild(th);
        });
        
        // Añadir filas de datos
        data.forEach((item, index) => {
            const row = document.createElement('tr');
            
            // Número de fila
            const indexCell = document.createElement('td');
            indexCell.textContent = index + 1;
            row.appendChild(indexCell);
            
            // ID
            const idCell = document.createElement('td');
            idCell.textContent = item._id || '';
            row.appendChild(idCell);
            
            // Resto de campos
            allKeys.forEach(key => {
                const cell = document.createElement('td');
                
                // Manejar valores complejos (objetos, arrays)
                if (item[key] !== undefined) {
                    if (typeof item[key] === 'object' && item[key] !== null) {
                        cell.textContent = JSON.stringify(item[key]);
                    } else {
                        cell.textContent = item[key];
                    }
                } else {
                    cell.textContent = '';
                }
                
                row.appendChild(cell);
            });
            
            tbody.appendChild(row);
        });
    } else {
        // Manejar otros tipos de resultados (insert, update, delete)
        resultsCount.textContent = '1 operación completada';
        
        const allKeys = Object.keys(data);
        
        // Añadir encabezados
        const headerRow = thead.querySelector('tr');
        allKeys.forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            headerRow.appendChild(th);
        });
        
        // Crear una única fila para mostrar el resultado
        const row = document.createElement('tr');
        
        // Número de fila
        const indexCell = document.createElement('td');
        indexCell.textContent = '1';
        row.appendChild(indexCell);
        
        // ID (vacío para operaciones)
        const idCell = document.createElement('td');
        idCell.textContent = '';
        row.appendChild(idCell);
        
        // Mostrar resultados de operación
        allKeys.forEach(key => {
            const cell = document.createElement('td');
            if (typeof data[key] === 'object' && data[key] !== null) {
                cell.textContent = JSON.stringify(data[key]);
            } else {
                cell.textContent = data[key];
            }
            row.appendChild(cell);
        });
        
        tbody.appendChild(row);
    }
}

// Funciones de utilidad para la interfaz
function setupEventListeners() {
    // Cambio de base de datos
    databaseSelect.addEventListener('change', () => {
        const selectedDB = databaseSelect.value;
        if (selectedDB) {
            loadCollections(selectedDB);
        } else {
            collectionSelect.innerHTML = '<option value="">Seleccionar colección...</option>';
            collectionsCount.textContent = '0';
        }
    });
    
    // Botón ejecutar
    executeBtn.addEventListener('click', executeQuery);
    
    // Botón limpiar
    clearBtn.addEventListener('click', () => {
        sqlQuery.value = '';
        mongoQueryDisplay.textContent = '// La consulta MongoDB aparecerá aquí';
        resultsTable.querySelector('tbody').innerHTML = '';
        resultsCount.textContent = '0 resultados encontrados';
    });
    
    // Cambio de pestaña
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            activateTab(tabId);
        });
    });
    
    // Exportar a JSON
    document.getElementById('export-json').addEventListener('click', () => {
        exportResults('json');
    });
    
    // Exportar a CSV
    document.getElementById('export-csv').addEventListener('click', () => {
        exportResults('csv');
    });
}

// Cambiar de pestaña
function activateTab(tabId) {
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    tabPanes.forEach(pane => {
        if (pane.id === tabId) {
            pane.classList.add('active');
        } else {
            pane.classList.remove('active');
        }
    });
}

// Mostrar loader
function showLoader() {
    loader.classList.add('show');
}

// Ocultar loader
function hideLoader() {
    loader.classList.remove('show');
}

// Mostrar notificación toast
function showToast(type, message) {
    toastMessage.textContent = message;
    
    // Establecer icono según tipo
    toastIcon.className = 'fa-solid';
    
    if (type === 'success') {
        toastIcon.classList.add('fa-check-circle', 'success');
    } else if (type === 'error') {
        toastIcon.classList.add('fa-exclamation-circle', 'error');
    } else {
        toastIcon.classList.add('fa-info-circle', 'info');
    }
    
    // Mostrar toast
    toast.classList.add('show');
    
    // Ocultar después de 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Exportar resultados
function exportResults(format) {
    const tbody = resultsTable.querySelector('tbody');
    
    if (!tbody.children.length) {
        showToast('info', 'No hay resultados para exportar');
        return;
    }
    
    try {
        const thead = resultsTable.querySelector('thead');
        const headers = Array.from(thead.querySelectorAll('th')).map(th => th.textContent);
        
        // Obtener datos de la tabla
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        if (format === 'json') {
            const jsonData = [];
            
            rows.forEach(row => {
                const rowData = {};
                const cells = Array.from(row.querySelectorAll('td'));
                
                // Empezar desde 2 para saltar el número de fila y el ID
                for (let i = 2; i < cells.length; i++) {
                    rowData[headers[i]] = cells[i].textContent;
                }
                
                jsonData.push(rowData);
            });
            
            // Crear y descargar archivo JSON
            const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
            downloadFile(blob, 'resultados.json');
            
            showToast('success', 'Datos exportados a JSON');
            
        } else if (format === 'csv') {
            let csvContent = '';
            
            // Encabezados (excluyendo # e ID)
            csvContent += headers.slice(2).join(',') + '\n';
            
            // Datos
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                const rowValues = cells.slice(2).map(cell => {
                    // Escapar comillas y encerrar en comillas si contiene comas
                    let value = cell.textContent.replace(/"/g, '""');
                    if (value.includes(',')) {
                        value = `"${value}"`;
                    }
                    return value;
                });
                
                csvContent += rowValues.join(',') + '\n';
            });
            
            // Crear y descargar archivo CSV
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
            downloadFile(blob, 'resultados.csv');
            
            showToast('success', 'Datos exportados a CSV');
        }
        
    } catch (error) {
        showToast('error', 'Error al exportar datos');
        console.error('Error:', error);
    }
}

// Función para descargar archivo
function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}