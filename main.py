from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_cors import CORS
import pymysql
from sqlalchemy import text
import json
import time

pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/appbdd?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def execute_query(query, args=(), one=False):
    result = db.session.execute(text(query), args)
    if one:
        return result.fetchone()
    return result.fetchall()

# Autenticación
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({
                'error': 'Datos incompletos',
                'message': 'Email y contraseña son requeridos'
            }), 400

        query = '''
            SELECT id, nombre, email, password, tipo 
            FROM usuarios 
            WHERE email = :email
        '''
        user = execute_query(query, {'email': data['email']}, one=True)

        if not user:
            return jsonify({
                'error': 'Usuario no encontrado',
                'message': 'El email proporcionado no está registrado'
            }), 401

        if user[3] != data['password']:
            return jsonify({
                'error': 'Contraseña incorrecta',
                'message': 'La contraseña proporcionada es incorrecta'
            }), 401

        return jsonify({
            'id': user[0],
            'nombre': user[1],
            'email': user[2],
            'tipo': user[4]
        })

    except Exception as e:
        print(f"Error en login: {str(e)}")  # Para debugging
        return jsonify({
            'error': 'Error del servidor',
            'message': 'Ocurrió un error al procesar la solicitud'
        }), 500

# Rutas para profesor

@app.route('/profesor/<int:profesor_id>/clases', methods=['GET'])
def get_clases_profesor(profesor_id):
    try:
        clases = execute_query('''
            SELECT 
                c.id, 
                c.nombre,
                (SELECT COUNT(DISTINCT i.alumno_id) 
                 FROM inscripciones i 
                 WHERE i.clase_id = c.id) as total_alumnos,
                (SELECT COUNT(DISTINCT a.alumno_id) 
                 FROM asistencias a 
                 WHERE a.clase_id = c.id 
                 AND a.fecha = CURRENT_DATE
                 AND a.estado = 'Presente') as presentes_hoy
            FROM clases c
            WHERE c.profesor_id = :profesor_id
            ORDER BY c.nombre
        ''', {'profesor_id': profesor_id})
        
        result = []
        for clase in clases:
            # Obtener última fecha de asistencia registrada
            ultima_asistencia = execute_query('''
                SELECT MAX(fecha) 
                FROM asistencias 
                WHERE clase_id = :clase_id
            ''', {'clase_id': clase[0]}, one=True)

            result.append({
                'id': clase[0],
                'nombre': clase[1],
                'total_alumnos': clase[2] or 0,
                'presentes_hoy': clase[3] or 0,
                'ultima_asistencia': ultima_asistencia[0].strftime('%Y-%m-%d') if ultima_asistencia[0] else None
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/profesor/<int:profesor_id>/clase/<int:clase_id>/resumen', methods=['GET'])
def get_resumen_clase(profesor_id, clase_id):
    try:
        # Verificar que la clase pertenece al profesor
        verificacion = execute_query('''
            SELECT 1 FROM clases 
            WHERE id = :clase_id AND profesor_id = :profesor_id
        ''', {'clase_id': clase_id, 'profesor_id': profesor_id}, one=True)
        
        if not verificacion:
            return jsonify({'error': 'Clase no encontrada'}), 404

        # Obtener resumen de asistencias
        resumen = execute_query('''
            SELECT 
                COUNT(DISTINCT a.alumno_id) as total_alumnos,
                COUNT(DISTINCT CASE WHEN a.estado = 'Presente' THEN a.alumno_id END) as presentes,
                COUNT(DISTINCT CASE WHEN a.estado = 'Ausente' THEN a.alumno_id END) as ausentes,
                DATE(a.fecha) as fecha
            FROM asistencias a
            WHERE a.clase_id = :clase_id
            GROUP BY DATE(a.fecha)
            ORDER BY fecha DESC
            LIMIT 7
        ''', {'clase_id': clase_id})

        return jsonify([{
            'fecha': r[3].strftime('%Y-%m-%d'),
            'total_alumnos': r[0],
            'presentes': r[1],
            'ausentes': r[2]
        } for r in resumen])
    except Exception as e:
        print(f"Error al obtener resumen de la clase: {str(e)}")  # Para debugging
        return jsonify({'error': str(e)}), 500

@app.route('/clases/<int:clase_id>/alumnos', methods=['GET'])
def get_alumnos_clase(clase_id):
    try:
        alumnos = execute_query('''
            SELECT DISTINCT 
                u.id, 
                u.nombre,
                u.email,
                (SELECT COUNT(*) 
                 FROM asistencias a 
                 WHERE a.alumno_id = u.id 
                 AND a.clase_id = :clase_id) as total_asistencias,
                (SELECT estado 
                 FROM asistencias a 
                 WHERE a.alumno_id = u.id 
                 AND a.clase_id = :clase_id 
                 ORDER BY a.fecha DESC 
                 LIMIT 1) as ultimo_estado,
                (SELECT fecha 
                 FROM asistencias a 
                 WHERE a.alumno_id = u.id 
                 AND a.clase_id = :clase_id 
                 ORDER BY a.fecha DESC 
                 LIMIT 1) as ultima_fecha
            FROM usuarios u
            JOIN alumnos a ON u.id = a.id
            JOIN inscripciones i ON a.id = i.alumno_id
            WHERE i.clase_id = :clase_id
            ORDER BY u.nombre
        ''', {'clase_id': clase_id})

        return jsonify([{
            'id': a[0],
            'nombre': a[1],
            'email': a[2],
            'total_asistencias': a[3] or 0,
            'ultimo_estado': a[4].lower() if a[4] else None,
            'ultima_fecha': a[5].strftime('%Y-%m-%d') if a[5] else None
        } for a in alumnos])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/profesor/<int:profesor_id>/clase/<int:clase_id>/resumen', methods=['GET'])
def get_resumen_asistencia_clase(profesor_id, clase_id):
    try:
        resumen = execute_query('''
            SELECT 
                a.fecha,
                COUNT(DISTINCT CASE WHEN a.estado = 'Presente' THEN a.alumno_id END) as presentes,
                COUNT(DISTINCT CASE WHEN a.estado = 'Ausente' THEN a.alumno_id END) as ausentes,
                (SELECT COUNT(DISTINCT alumno_id) 
                 FROM inscripciones 
                 WHERE clase_id = :clase_id) as total_alumnos
            FROM asistencias a
            WHERE a.clase_id = :clase_id
            GROUP BY a.fecha
            ORDER BY a.fecha DESC
            LIMIT 7
        ''', {'clase_id': clase_id})

        return jsonify([{
            'fecha': r[0].strftime('%Y-%m-%d'),
            'presentes': r[1] or 0,
            'ausentes': r[2] or 0,
            'total_alumnos': r[3] or 0
        } for r in resumen])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rutas para alumnos
@app.route('/alumno/<int:alumno_id>/clases', methods=['GET'])
def get_clases_alumno(alumno_id):
    try:
        clases = execute_query('''
            SELECT DISTINCT 
                c.id, 
                c.nombre, 
                u.nombre as profesor,
                (SELECT fecha 
                 FROM asistencias 
                 WHERE alumno_id = :alumno_id 
                 AND clase_id = c.id 
                 ORDER BY fecha DESC 
                 LIMIT 1) as ultima_asistencia
            FROM clases c
            JOIN inscripciones i ON c.id = i.clase_id
            JOIN profesores p ON c.profesor_id = p.id
            JOIN usuarios u ON p.id = u.id
            WHERE i.alumno_id = :alumno_id
            ORDER BY c.nombre
        ''', {'alumno_id': alumno_id})
        
        return jsonify([{
            'id': c[0],
            'nombre': c[1],
            'profesor': c[2],
            'ultimaAsistencia': c[3].strftime('%Y-%m-%d') if c[3] else None
        } for c in clases])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/asistencia/<int:alumno_id>/<int:clase_id>', methods=['GET'])
def get_asistencia_alumno(alumno_id, clase_id):
    try:
        asistencias = execute_query('''
            SELECT fecha, estado 
            FROM asistencias 
            WHERE alumno_id = :alumno_id 
            AND clase_id = :clase_id
            ORDER BY fecha DESC
        ''', {
            'alumno_id': alumno_id,
            'clase_id': clase_id
        })
        
        return jsonify([{
            'fecha': a[0].strftime('%Y-%m-%d'),
            'estado': a[1]
        } for a in asistencias])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/alumno/<int:alumno_id>/estadisticas', methods=['GET'])
def get_estadisticas_alumno(alumno_id):
    try:
        # Estadísticas generales
        stats = execute_query('''
            SELECT 
                c.id,
                c.nombre,
                COUNT(*) as total_clases,
                SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) as presentes,
                SUM(CASE WHEN a.estado = 'Ausente' THEN 1 ELSE 0 END) as ausentes
            FROM asistencias a
            JOIN clases c ON a.clase_id = c.id
            WHERE a.alumno_id = :alumno_id
            GROUP BY c.id, c.nombre
        ''', {'alumno_id': alumno_id})
        
        return jsonify([{
            'clase_id': s[0],
            'clase_nombre': s[1],
            'total_clases': s[2],
            'presentes': s[3],
            'ausentes': s[4],
            'porcentaje_asistencia': round((s[3] / s[2]) * 100, 2) if s[2] > 0 else 0
        } for s in stats])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rutas para registro de asistencia y QR
@app.route('/registrar-asistencia-qr', methods=['POST'])
def registrar_asistencia_qr():
    data = request.json
    try:
        # Decodificar datos del QR
        qr_data = json.loads(data['qrData'])
        
        # Validar tiempo del QR (5 minutos)
        timestamp = qr_data.get('timestamp', 0)
        current_time = time.time() * 1000
        if current_time - timestamp > 300000:
            return jsonify({'error': 'Código QR expirado'}), 400

        # Verificar si el alumno está inscrito en la clase
        inscripcion = execute_query('''
            SELECT 1 FROM inscripciones 
            WHERE alumno_id = :alumno_id AND clase_id = :clase_id
        ''', {
            'alumno_id': data['alumnoId'],
            'clase_id': qr_data['clase_id']
        }, one=True)

        if not inscripcion:
            return jsonify({'error': 'Alumno no inscrito en esta clase'}), 400

        # Verificar si ya existe asistencia para hoy
        asistencia_existente = execute_query('''
            SELECT 1 FROM asistencias 
            WHERE alumno_id = :alumno_id 
            AND clase_id = :clase_id 
            AND fecha = CURRENT_DATE()
        ''', {
            'alumno_id': data['alumnoId'],
            'clase_id': qr_data['clase_id']
        }, one=True)

        if asistencia_existente:
            return jsonify({'error': 'Ya se registró asistencia hoy para esta clase'}), 400

        # Registrar asistencia
        query = '''
            INSERT INTO asistencias (alumno_id, clase_id, fecha, estado)
            VALUES (:alumno_id, :clase_id, CURRENT_DATE(), 'Presente')
        '''
        db.session.execute(text(query), {
            'alumno_id': data['alumnoId'],
            'clase_id': qr_data['clase_id']
        })
        db.session.commit()
        
        return jsonify({'message': 'Asistencia registrada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/profesor/<int:profesor_id>/asistencia/<int:clase_id>', methods=['GET'])
def get_asistencia_clase(profesor_id, clase_id):
    try:
        # Verificar que la clase pertenezca al profesor
        verificacion = execute_query('''
            SELECT 1 FROM clases 
            WHERE id = :clase_id AND profesor_id = :profesor_id
        ''', {
            'clase_id': clase_id,
            'profesor_id': profesor_id
        }, one=True)

        if not verificacion:
            return jsonify({
                'error': 'No autorizado',
                'message': 'Esta clase no pertenece al profesor'
            }), 403

        # Obtener lista de alumnos inscritos y sus asistencias
        asistencias = execute_query('''
            SELECT 
                u.id as alumno_id,
                u.nombre as alumno_nombre,
                (SELECT COUNT(*) 
                 FROM asistencias a 
                 WHERE a.alumno_id = u.id 
                 AND a.clase_id = :clase_id) as total_asistencias,
                (SELECT GROUP_CONCAT(
                    JSON_OBJECT(
                        'fecha', DATE_FORMAT(a2.fecha, '%Y-%m-%d'),
                        'estado', LOWER(a2.estado)
                    )
                    ORDER BY a2.fecha DESC
                ) 
                 FROM asistencias a2 
                 WHERE a2.alumno_id = u.id 
                 AND a2.clase_id = :clase_id) as asistencias_json
            FROM usuarios u
            JOIN alumnos al ON u.id = al.id
            JOIN inscripciones i ON al.id = i.alumno_id
            WHERE i.clase_id = :clase_id
            GROUP BY u.id, u.nombre
            ORDER BY u.nombre
        ''', {'clase_id': clase_id})

        # Procesar los resultados
        result = []
        for row in asistencias:
            alumno_data = {
                'alumno_id': row[0],
                'alumno_nombre': row[1],
                'total_asistencias': row[2] or 0,
                'asistencias': []
            }

            # Procesar el JSON de asistencias si existe
            if row[3]:  # asistencias_json
                try:
                    import json
                    asistencias_list = json.loads('[' + row[3] + ']')
                    alumno_data['asistencias'] = asistencias_list
                except Exception as e:
                    print(f"Error procesando JSON de asistencias: {str(e)}")
                    alumno_data['asistencias'] = []

            result.append(alumno_data)

        if not result:
            # Si no hay alumnos, devolver lista vacía pero con status 200
            return jsonify([])

        return jsonify(result)

    except Exception as e:
        print(f"Error en asistencias: {str(e)}")  # Para debugging
        import traceback
        traceback.print_exc()  # Imprimir stack trace completo
        return jsonify({
            'error': 'Error del servidor',
            'message': str(e)
        }), 500

@app.route('/profesor/<int:profesor_id>/clase/<int:clase_id>/resumen-dia', methods=['GET'])
def get_resumen_dia(profesor_id, clase_id):
    try:
        # Verificar que la clase pertenece al profesor
        verificacion = execute_query('''
            SELECT 1 FROM clases 
            WHERE id = :clase_id AND profesor_id = :profesor_id
        ''', {
            'clase_id': clase_id,
            'profesor_id': profesor_id
        }, one=True)

        if not verificacion:
            return jsonify({
                'error': 'No autorizado',
                'message': 'Esta clase no pertenece al profesor'
            }), 403

        # Obtener el resumen del día
        resumen = execute_query('''
            SELECT 
                COUNT(DISTINCT i.alumno_id) as total_alumnos,
                COUNT(DISTINCT CASE WHEN a.estado = 'Presente' THEN a.alumno_id END) as presentes,
                COUNT(DISTINCT CASE WHEN a.estado = 'Ausente' THEN a.alumno_id END) as ausentes
            FROM inscripciones i
            LEFT JOIN asistencias a ON i.alumno_id = a.alumno_id 
                AND i.clase_id = a.clase_id
                AND DATE(a.fecha) = CURRENT_DATE
            WHERE i.clase_id = :clase_id
        ''', {'clase_id': clase_id}, one=True)

        return jsonify({
            'total_alumnos': resumen[0] or 0,
            'presentes': resumen[1] or 0,
            'ausentes': resumen[2] or 0,
            'fecha': datetime.now().strftime('%Y-%m-%d')
        })

    except Exception as e:
        print(f"Error en resumen: {str(e)}")  # Para debugging
        return jsonify({
            'error': 'Error del servidor',
            'message': str(e)
        }), 500

@app.route('/profesor/<int:profesor_id>/clase/<int:clase_id>/asistencia', methods=['POST'])
def registrar_asistencia_profesor(profesor_id, clase_id):
    try:
        data = request.json
        if not data or 'alumno_id' not in data or 'estado' not in data:
            return jsonify({
                'error': 'Datos incompletos',
                'message': 'Se requiere alumno_id y estado'
            }), 400

        # Verificar que la clase pertenece al profesor
        verificacion = execute_query('''
            SELECT 1 FROM clases 
            WHERE id = :clase_id AND profesor_id = :profesor_id
        ''', {
            'clase_id': clase_id,
            'profesor_id': profesor_id
        }, one=True)

        if not verificacion:
            return jsonify({
                'error': 'No autorizado',
                'message': 'Esta clase no pertenece al profesor'
            }), 403

        # Registrar asistencia
        db.session.execute(text('''
            INSERT INTO asistencias (alumno_id, clase_id, fecha, estado)
            VALUES (:alumno_id, :clase_id, CURRENT_DATE, :estado)
            ON DUPLICATE KEY UPDATE estado = :estado
        '''), {
            'alumno_id': data['alumno_id'],
            'clase_id': clase_id,
            'estado': data['estado']
        })
        db.session.commit()

        return jsonify({
            'message': 'Asistencia registrada correctamente'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error al registrar asistencia: {str(e)}")  # Para debugging
        return jsonify({
            'error': 'Error del servidor',
            'message': str(e)
        }), 500


@app.route('/clases/<int:clase_id>/horarios', methods=['GET'])
def get_horarios_clase(clase_id):
    try:
        # Primero verificamos que la clase exista
        clase = execute_query('''
            SELECT nombre FROM clases WHERE id = :clase_id
        ''', {'clase_id': clase_id}, one=True)

        if not clase:
            return jsonify({
                'error': 'Clase no encontrada',
                'message': 'La clase especificada no existe'
            }), 404

        # Obtenemos los horarios
        horarios = execute_query('''
            SELECT 
                h.dia_semana,
                TIME_FORMAT(h.hora_inicio, '%H:%i') as hora_inicio,
                TIME_FORMAT(h.hora_fin, '%H:%i') as hora_fin
            FROM horarios h
            WHERE h.clase_id = :clase_id
            ORDER BY 
                CASE h.dia_semana
                    WHEN 'Lunes' THEN 1
                    WHEN 'Martes' THEN 2
                    WHEN 'Miércoles' THEN 3
                    WHEN 'Jueves' THEN 4
                    WHEN 'Viernes' THEN 5
                    WHEN 'Sábado' THEN 6
                    WHEN 'Domingo' THEN 7
                END,
                h.hora_inicio
        ''', {'clase_id': clase_id})

        # Procesamos los resultados
        result = []
        for horario in horarios:
            result.append({
                'dia_semana': horario[0],
                'hora_inicio': horario[1],
                'hora_fin': horario[2]
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error al obtener horarios: {str(e)}")  # Para debugging
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Error del servidor',
            'message': str(e)
        }), 500

# ... Resto de las rutas existentes ...

@app.route('/change-password', methods=['POST'])
def change_password():
    data = request.json
    try:
        # Verificar contraseña actual
        user = execute_query('''
            SELECT id FROM usuarios 
            WHERE email = :email AND password = :old_password
        ''', {
            'email': data['email'],
            'old_password': data['oldPassword']
        }, one=True)

        if not user:
            return jsonify({'error': 'Contraseña actual incorrecta'}), 400

        # Actualizar contraseña
        update_query = '''
            UPDATE usuarios 
            SET password = :new_password 
            WHERE email = :email
        '''
        db.session.execute(text(update_query), {
            'email': data['email'],
            'new_password': data['newPassword']
        })
        db.session.commit()
        return jsonify({'message': 'Contraseña actualizada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# También vamos a verificar los horarios en la base de datos
@app.route('/debug/horarios/<int:clase_id>', methods=['GET'])
def debug_horarios(clase_id):
    try:
        horarios_raw = execute_query('''
            SELECT 
                h.id,
                h.dia_semana,
                h.hora_inicio,
                h.hora_fin,
                c.nombre as clase
            FROM horarios h
            JOIN clases c ON h.clase_id = c.id
            WHERE h.clase_id = :clase_id
        ''', {'clase_id': clase_id})
        
        return jsonify({
            'horarios_raw': [
                {
                    'id': h[0],
                    'dia_semana': h[1],
                    'hora_inicio': str(h[2]),
                    'hora_fin': str(h[3]),
                    'clase': h[4]
                }
                for h in horarios_raw
            ]
        })

    except Exception as e:
        return jsonify({
            'error': 'Error en debug',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)