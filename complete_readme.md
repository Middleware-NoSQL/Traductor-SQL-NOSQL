# 🔄 Traductor SQL-NoSQL

## 📋 Descripción

Sistema web para traducir consultas SQL a operaciones MongoDB equivalentes. Permite convertir consultas SELECT, INSERT, UPDATE, DELETE y CREATE TABLE de SQL a sintaxis MongoDB con validación y ejecución en tiempo real.

## 🏗️ Arquitectura del Proyecto



## 🚀 Instalación Rápida

### 📋 Prerrequisitos

- **Python 3.8+** 
- **Node.js 16+**
- **MongoDB 4.4+** (local o remoto)

### ⚡ Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/traductor-sql-nosql.git
cd traductor-sql-nosql

# 2. Backend
cd Backend
pip install -r requirements.txt
python main.py

# 3. Frontend (nueva terminal)
cd ../Frontend
npm install
npm run dev
```

**¡Listo! Accede a http://localhost:3000** 🎉

## 🔧 Configuración Detallada

### 🐍 Backend (Python + Flask)

```bash
cd Backend

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno (opcional)
cp .env.example .env

# Ejecutar servidor
python main.py
```

**Servidor corriendo en:** `http://localhost:5000`

### 🌐 Frontend (Vue.js Vanilla + Vite)

```bash
cd Frontend

# Instalar dependencias
npm install

# Desarrollo con hot-reload
npm run dev

# Build para producción
npm run build

# Preview build
npm run preview
```

**Aplicación corriendo en:** `http://localhost:3000`

## 📦 Dependencias

### Backend - requirements.txt
```txt
Flask==2.3.3
Flask-CORS==4.0.0
pymongo==4.5.0
PyJWT==2.8.0
python-dotenv==1.0.0
bcrypt==4.0.1
```

### Frontend - package.json
```json
{
  "name": "traductor-sql-nosql-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "serve": "vite preview --port 3000"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  },
  "dependencies": {
    "axios": "^1.6.0"
  }
}
```

## ⚙️ Configuración

### Backend (.env)

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=sql_middleware_auth

# JWT
JWT_SECRET_KEY=tu_clave_secreta_aqui
JWT_EXPIRATION_HOURS=24

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
```

### Frontend (vite.config.js)

```javascript
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:5000'
    }
  },
  build: {
    outDir: 'dist'
  }
})
```

## 🔧 Funcionalidades

### ✅ Consultas SQL Soportadas

| Tipo | Ejemplo | Estado |
|------|---------|--------|
| **CREATE TABLE** | `CREATE TABLE productos (id INT, nombre VARCHAR(100))` | ✅ |
| **INSERT** | `INSERT INTO productos VALUES (1, 'Laptop')` | ✅ |
| **SELECT** | `SELECT * FROM productos WHERE precio > 100` | ✅ |
| **UPDATE** | `UPDATE productos SET precio = 1200 WHERE id = 1` | ✅ |
| **DELETE** | `DELETE FROM productos WHERE activo = false` | ✅ |

## 🐛 Solución de Problemas

### Error: "Module not found"

```bash
# Backend
cd Backend
pip install -r requirements.txt

# Frontend
cd Frontend
npm install
```

### Puerto en uso

```bash
# Cambiar puerto backend
export FLASK_PORT=5001
python main.py

# Cambiar puerto frontend
npm run dev -- --port 3001
```

### MongoDB no conecta

```bash
# Verificar MongoDB
mongod --version
mongod --dbpath /data/db

# O usar MongoDB Atlas
# Editar MONGODB_URI en .env
```

## 📊 Scripts Disponibles

### Backend
```bash
python main.py              # Iniciar servidor
python -m pytest tests/     # Ejecutar tests
python -m pip freeze        # Ver dependencias
```

### Frontend
```bash
npm run dev         # Desarrollo con hot-reload
npm run build       # Build para producción
npm run preview     # Preview del build
npm install         # Instalar dependencias
npm update          # Actualizar dependencias
```

## 🔒 Producción

### Backend
```bash
# Usar servidor WSGI
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

### Frontend
```bash
# Build y servir
npm run build
npm run preview

# O usar nginx/apache para servir dist/
```

## 🚀 Docker (Opcional)

### Dockerfile.backend
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "main.py"]
```

### Dockerfile.frontend
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./Backend
    ports:
      - "5000:5000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/
    depends_on:
      - mongo
  
  frontend:
    build: ./Frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
  
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

```bash
# Ejecutar con Docker
docker-compose up -d
```

## 🤝 Desarrollo

### Workflow
```bash
# 1. Backend (Terminal 1)
cd Backend
pip install -r requirements.txt
python main.py

# 2. Frontend (Terminal 2) 
cd Frontend
npm install
npm run dev

# 3. MongoDB (Terminal 3)
mongod

# 4. Acceder a http://localhost:3000
```

### Estructura de Desarrollo
```
📁 Backend/
├── requirements.txt    # pip install -r requirements.txt
├── main.py            # python main.py
└── .env              # Configuración

📁 Frontend/
├── package.json       # npm install
├── vite.config.js     # npm run dev
└── src/              # Código fuente
```

## 📄 Licencia

MIT License - ver `LICENSE` para detalles.

## 👥 Autor

**Erik Chalacama** - Escuela Politécnica Nacional

---

### 🚀 TL;DR

```bash
# Backend
cd Backend && pip install -r requirements.txt && python main.py

# Frontend  
cd Frontend && npm install && npm run dev

# ¡Listo! → http://localhost:3000
```