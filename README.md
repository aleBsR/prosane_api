# PROSANE API (Backend)

Este es el backend para la aplicación del circuito PROSANE (Programa Nacional de Salud Escolar) en Salta Capital.

## Tecnologías Utilizadas
- **Django 6.x**
- **Django REST Framework (DRF)**
- **PostgreSQL**

## Descripción del Proyecto
La API de PROSANE expone los endpoints necesarios para que la aplicación móvil (Flutter) interactúe con el sistema central. Funciona como una capa intermedia entre los usuarios finales y los posibles sistemas provinciales (SISA, REFEPS, RENAPER).

### Características Principales (Planificadas)
- Autenticación mediante JWT y gestión de roles (Familia, Escuela, Salud, Admin).
- Endpoints CRUD para gestión de instituciones, familias y alumnos.
- Recepción y almacenamiento de los bloques clínicos (Control Integral de Salud - CIS).
- Integración en capa de servicios con RENAPER (validación de identidad) y REFEPS (validación de matrículas médicas).
- Generación de constancias en formato PDF con trazabilidad (hash + timestamp).

## Configuración y Entornos
Este proyecto separa sus configuraciones en módulos según el entorno:
- `config.settings.local`: Usado por defecto para desarrollo local (`manage.py`).
- `config.settings.production`: Usado en entornos desplegados (ej. Railway o Render), invocado por `wsgi.py` y `asgi.py`.

### Instalación Local
1. Clona el repositorio.
2. Crea el entorno virtual: `python3 -m venv venv`
3. Activa el entorno: `source venv/bin/activate` (en Linux/Mac) o `venv\Scripts\activate` (en Windows).
4. Instala dependencias: `pip install -r requirements.txt` *(Nota: archivo por crear)*
5. Ejecuta migraciones: `python manage.py migrate`
6. Levanta el servidor: `python manage.py runserver`
