# Sistema de Asistencia - Backend API

## Descripción
Backend del sistema de asistencia desarrollado con Flask y MySQL. Esta API proporciona endpoints para gestionar la asistencia de alumnos en clases, autenticación de usuarios, y generación de reportes estadísticos.

## Tecnologías Utilizadas
- Flask (Framework Python)
- MySQL (Base de datos)
- SQLAlchemy (ORM)
- PyMySQL
- Flask-CORS

## Requisitos Previos
- Python 3.x
- MySQL Server
- Base de datos 'appbdd' creada

## Configuración
1. Instalar dependencias:
```bash
pip install flask flask-sqlalchemy flask-cors pymysql
```

2. Configurar la base de datos en `main.py`:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/appbdd?charset=utf8mb4'
```

## Estructura de Endpoints

### Autenticación
- `POST /login` - Iniciar sesión de usuario

### Rutas para Profesores
- `GET /profesor/<profesor_id>/clases` - Obtener lista de clases del profesor
- `GET /profesor/<profesor_id>/clase/<clase_id>/resumen` - Obtener resumen de asistencia de una clase
- `GET /clases/<clase_id>/alumnos` - Obtener lista de alumnos en una clase
- `GET /profesor/<profesor_id>/clase/<clase_id>/resumen-dia` - Obtener resumen del día actual
- `POST /profesor/<profesor_id>/clase/<clase_id>/asistencia` - Registrar asistencia por el profesor

### Rutas para Alumnos
- `GET /alumno/<alumno_id>/clases` - Obtener clases del alumno
- `GET /asistencia/<alumno_id>/<clase_id>` - Obtener asistencias del alumno en una clase
- `GET /alumno/<alumno_id>/estadisticas` - Obtener estadísticas de asistencia
- `POST /registrar-asistencia-qr` - Registrar asistencia mediante QR

### Gestión de Horarios
- `GET /clases/<clase_id>/horarios` - Obtener horarios de una clase

### Gestión de Usuario
- `POST /change-password` - Cambiar contraseña de usuario

## Características Principales
- Autenticación de usuarios (profesores y alumnos)
- Registro de asistencia mediante QR
- Registro manual de asistencia por profesores
- Generación de estadísticas y reportes
- Control de horarios de clases
- Manejo de múltiples clases y alumnos

## Seguridad
- Validación de pertenencia de clases a profesores
- Verificación de inscripción de alumnos en clases
- Validación de tiempo en códigos QR (5 minutos)
- Prevención de registro duplicado de asistencia

## Formato de Respuestas
Las respuestas siguen un formato JSON consistente:
```json
{
    "data": {}, // Datos solicitados
    "error": "mensaje", // En caso de error
    "message": "descripción" // Mensajes informativos
}
```

## Manejo de Errores
- 400: Bad Request - Datos incorrectos o incompletos
- 401: Unauthorized - Credenciales inválidas
- 403: Forbidden - No autorizado para acceder al recurso
- 404: Not Found - Recurso no encontrado
- 500: Internal Server Error - Error del servidor

## Ejecución
```bash
python main.py
```
El servidor se iniciará en `http://localhost:5000`

## Desarrollo y Debugging
- Modo debug activado para desarrollo
- Logs detallados de errores
- Endpoint de debug para horarios: `/debug/horarios/<clase_id>`

## Consideraciones para Ionic/Angular
- CORS habilitado para permitir peticiones desde el frontend
- Todas las respuestas incluyen los headers necesarios para CORS
- Formato JSON consistente para facilitar el manejo en el frontend
- Endpoints diseñados para optimizar las peticiones desde la app móvil

## Recomendaciones
1. Configurar variables de entorno para credenciales de base de datos
2. Implementar rate limiting para endpoints críticos
3. Agregar más validaciones de seguridad según necesidades
4. Considerar implementar caché para optimizar rendimiento
