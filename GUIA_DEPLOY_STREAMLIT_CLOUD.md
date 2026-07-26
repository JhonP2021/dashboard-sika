# 🚀 Guía: Desplegar Dashboard Sika en Streamlit Cloud

## Paso 1: Preparar el Repositorio (✅ YA HECHO)

Tu repositorio está listo en:
```
https://github.com/JhonP2021/dashboard-sika
```

---

## Paso 2: Crear un archivo `streamlit_config.toml`

Streamlit necesita configuración para la memoria caché. Crea el archivo:

```
.streamlit/config.toml
```

Con este contenido:

```toml
[client]
showErrorDetails = true

[logger]
level = "info"

[server]
port = 8501
headless = true
runOnSave = true
maxUploadSize = 200

[client]
toolbarMode = "viewer"

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

---

## Paso 3: Crear archivo `secrets.toml`

Streamlit Cloud necesita variables de entorno. Crea:

```
.streamlit/secrets.toml
```

Con este contenido (IMPORTANTE: Esta será la configuración para producción):

```toml
# Modo de la app
DASHBOARD_MODE = "PROD"

# Ruta a la base de datos Access (en producción)
# IMPORTANTE: En Streamlit Cloud NO TENDRÁS acceso a archivos locales
# Necesitarás conectarte a una base de datos remota (Cloud Database)
# Por ahora, usa CSV en Streamlit Cloud

# Si usas CSV:
# Los archivos CSV deben estar en el repositorio Git
# (pero EXCLUYÉLOS de .gitignore si son grandes)

# Si usas Access (recomendado para PROD):
# Necesitarás una base de datos en la nube:
# - Azure SQL Database
# - AWS RDS
# - PostgreSQL (Heroku/Railway)
# - MongoDB (Atlas)
```

---

## Paso 4: Actualizar requirements.txt

Streamlit Cloud necesita saber todas las dependencias. Verifica que tenga:

```txt
streamlit>=1.31.0
pandas>=2.1.0
plotly>=5.18.0
pyodbc>=5.1.0
```

⚠️ **NOTA IMPORTANTE**: `pyodbc` requiere drivers ODBC. En Streamlit Cloud:
- Si necesitas Access: Usa PyODBC + driver Docker personalizado (complejo)
- **RECOMENDADO**: Migra a una base de datos en la nube

---

## Paso 5: Conectar Streamlit Cloud

### 5.1 Crea una cuenta en Streamlit Cloud

1. Ve a https://streamlit.io/cloud
2. Haz clic en "Sign up"
3. Selecciona "GitHub" para conectar tu cuenta
4. Autoriza Streamlit a acceder a tus repositorios

### 5.2 Deploya tu app

1. En Streamlit Cloud, haz clic en **"New app"**
2. Selecciona:
   - **Repository**: `JhonP2021/dashboard-sika`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. Haz clic en **"Deploy"**

Streamlit empezará a construir tu app (tarda ~3 minutos en el primer deploy)

### 5.3 Obtén tu URL pública

Una vez desplegada, tu app estará en:
```
https://dashboard-sika.streamlit.app
```

---

## Paso 6: Configurar Secretos en Streamlit Cloud

1. En la sección de tu app en Streamlit Cloud
2. Haz clic en los **"..."** (más opciones)
3. Selecciona **"Settings"**
4. Ve a la sección **"Secrets"**
5. Pega el contenido de `.streamlit/secrets.toml`

```toml
DASHBOARD_MODE = "PROD"
# Agrega aquí la conexión a tu base de datos si la tienes
```

---

## Paso 7: Resolver Problema de Datos en Producción

**Problema**: Los archivos CSV están en tu máquina local, no en GitHub (por `.gitignore`)

**Soluciones**:

### Opción A: Usar CSV en GitHub (Simple, para DEV)

1. Edita `.gitignore` y comenta las líneas de CSV:
```gitignore
# *.csv  ← Comenta esta línea
# _Table*.csv  ← Comenta esta línea
```

2. Haz un commit y push:
```bash
git add .gitignore
git add *.csv
git commit -m "Add CSV files for deployment"
git push origin main
```

✅ Los CSVs ahora estarán disponibles en Streamlit Cloud

### Opción B: Conectar a una Base de Datos en la Nube (Profesional)

**Migra Access a una BD cloud**:

**PostgreSQL (recomendado):**
- Railway: https://railway.app (fácil, gratis)
- Heroku: https://heroku.com

**Pasos:**
1. Crea una BD en Railway/Heroku
2. Exporta datos de Access a PostgreSQL
3. Modifica `config/settings.py` para usar PostgreSQL
4. Agrega la conexión en `.streamlit/secrets.toml`

**Ejemplo con PostgreSQL:**
```python
# En config/settings.py
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
```

---

## Paso 8: Actualizar Código para Streamlit Cloud

Modifica `app.py` para detectar el entorno:

```python
import os

# Detectar entorno
ENV = os.getenv("STREAMLIT_ENV", "DEV")

if ENV == "PROD":
    # En cloud, usan datos de URL o base de datos
    data_source = "cloud_database"
else:
    # Localmente, usan CSV
    data_source = "local_csv"
```

---

## Paso 9: Activar Auto-Deploy

En Streamlit Cloud, cualquier push a `main` se desplegará automáticamente.

Para deshabilitar:
- Settings → "Advanced settings" → "Auto-rerun"

---

## Paso 10: Monitorear tu App

1. Logs en vivo: https://dashboard-sika.streamlit.app (en Settings)
2. Uso de CPU/Memoria
3. Errores de ejecución

---

## 🐛 Troubleshooting

| Error | Solución |
|-------|----------|
| **"ModuleNotFoundError"** | Agrega el módulo a `requirements.txt` y redeploy |
| **"Database connection failed"** | Verifica `secrets.toml` y credenciales |
| **"CSV not found"** | Agrega CSVs al repositorio (no en .gitignore) |
| **"App crashes after 1 min"** | Puede ser por timeout. Agrega `@st.cache_data` |

---

## ✅ Próximos Pasos

- [ ] Commit y push de config files
- [ ] Crear cuenta en Streamlit Cloud
- [ ] Conectar GitHub
- [ ] Desplegar app
- [ ] Configurar secretos
- [ ] Resolver acceso a datos
- [ ] Compartir URL pública con cliente

---

## 📊 URL Final para tu Cliente

```
https://dashboard-sika.streamlit.app
```

(La URL real será generada después de desplegar)

