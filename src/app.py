from flask import Flask, jsonify, request
from config import config
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime




app = Flask(__name__)
conexion = MySQL(app)


@app.route('/registro', methods=['POST'])
def registrar_usuario():
    try:
        cursor = conexion.connection.cursor()
        hashed_password = generate_password_hash(request.json['contrasena'])
        
        sql = "INSERT INTO usuarios (usuario, email, contrasena, rol) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (request.json['usuario'], request.json['email'], hashed_password, request.json['rol']))
        
        conexion.connection.commit()
        
        return jsonify({'mensaje': "Usuario registrado exitosamente"})
    except Exception as ex:
        return "Error"

@app.route('/main', methods = ['GET'])
def main():
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT * FROM usuarios"
        cursor.execute(sql)
        datos=cursor.fetchall()
        usuarios = []
        for fila in datos:
            usuario = {'id':fila[0], 'usuario':fila[1], 'email':fila[2], 'rol':fila[4]}
            usuarios.append(usuario)
        return jsonify(usuarios)
    except Exception as ex:
        return "Error"



@app.route('/main/<codigo>', methods = ['GET'])
def leer_usuario(codigo):
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT * FROM usuarios where id = '{0}'".format(codigo)      
        cursor.execute(sql)
        datos = cursor.fetchone()
        if datos != None:
            usuario = {'id':datos[0], 'usuario':datos[1], 'email':datos[2], 'rol':datos[4]}
            return jsonify({'usuario': usuario,'mensaje':"Usuario encontrado"}) 
        else:
            return jsonify({'mensaje': "Usuario no encontrado"})    
    except Exception as ex:
        return "Error"


@app.route('/eliminar_usuario/<codigo>', methods = ['DELETE'])
def eliminar_usuario(codigo):
    try:
        cursor = conexion.connection.cursor()
        sql = "DELETE FROM usuarios where id = '{0}'".format(codigo)
        cursor.execute(sql)
        conexion.connection.commit()
        return jsonify({'mensaje':"Usuario eliminado"})
    except Exception as ex:
        return "Error"     
    

@app.route('/actualizar_usuario/<codigo>', methods=['PUT'])
def actualizar_usuario(codigo):
    try:
        cursor = conexion.connection.cursor()
        usuario = request.json['usuario']
        email = request.json['email']
        
        nueva_contrasena = request.json.get('contrasena')
        if nueva_contrasena:
            nueva_contrasena = generate_password_hash(nueva_contrasena)
        
        sql = "UPDATE usuarios SET usuario = %s, email = %s"
        params = [usuario, email]

        if nueva_contrasena:
            sql += ", contrasena = %s"
            params.append(nueva_contrasena)
        
        sql += " WHERE id = %s"
        params.append(codigo)
        
        cursor.execute(sql, params)
        conexion.connection.commit()
        return jsonify({'mensaje': "Usuario actualizado"})
    except Exception as ex:
        return "Error"
  
    

@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.json.get('email')
        password = request.json.get('contrasena')

        cursor = conexion.connection.cursor()
        cursor.execute("SELECT id, contrasena FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()

        if usuario:
            hashed_password = usuario[1]
            if check_password_hash(hashed_password, password):
                return jsonify({'mensaje': 'Usuario logueado correctamente'})
            else:
                return jsonify({'mensaje': 'Usuario o contraseña incorrectos'}), 401
        else:
            return jsonify({'mensaje': 'Usuario o contraseña incorrectos'}), 401

    except Exception as ex:
        return jsonify({'mensaje': 'Error en el servidor'}), 500
    

@app.route('/crear_proyecto/<codigo>', methods=['POST'])
def crear_proyecto(codigo):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (codigo,))
        rol_usuario = cursor.fetchone()

        if rol_usuario[0] == 1:
            nombre = request.json['nombre']
            descripcion = request.json['descripcion']
            fecha_inicio = datetime.strptime(request.json['fecha_inicio'], '%Y-%m-%d').date()

            cursor.execute("INSERT INTO proyectos (nombre, descripcion, fecha_inicio, gerente) VALUES (%s, %s, %s, %s)",
                           (nombre, descripcion, fecha_inicio, codigo))
            conexion.connection.commit()
            return jsonify({'mensaje': 'Proyecto creado correctamente'})
        else:
            return jsonify({'mensaje': 'Usuario no tiene permisos para crear proyectos'}), 403
    except Exception as ex:
        return "Error"    
    

@app.route('/asignar_usuario/<codigo1>/<codigo2>', methods=['POST'])
def asignar_usuario(codigo1, codigo2):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (codigo1,))
        rol_usuario = cursor.fetchone()

        if rol_usuario and rol_usuario[0] == 1:
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (codigo2,))
            proyecto_existente = cursor.fetchone()

            if proyecto_existente:
                usuario_id = request.json.get('usuario_id')

                cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
                rol_usuario_asignado = cursor.fetchone()

                if rol_usuario_asignado and rol_usuario_asignado[0] == 2:
                    cursor.execute("SELECT 1 FROM usuarios_proyectos WHERE usuario = %s AND proyecto = %s", (usuario_id, codigo2))
                    asignacion_existente = cursor.fetchone()

                    if asignacion_existente:
                        return jsonify({'mensaje': 'El usuario ya está asignado a este proyecto'}), 400
                    else:
                        cursor.execute("INSERT INTO usuarios_proyectos (usuario, proyecto) VALUES (%s, %s)", (usuario_id, codigo2))
                        conexion.connection.commit()

                        cursor.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
                        nombre_usuario = cursor.fetchone()

                        return jsonify({'mensaje': f"Usuario {nombre_usuario[0]} asignado correctamente al proyecto {codigo2}"})
                else:
                    return jsonify({'mensaje': 'El usuario a asignar debe tener el rol 2 (desarrollador)'}), 403
            else:
                return jsonify({'mensaje': 'El proyecto especificado no existe'}), 404
        else:
            return jsonify({'mensaje': 'El usuario no tiene permisos para asignar usuarios al proyecto'}), 403
    except Exception as ex:
        return jsonify({'mensaje': 'Error en el servidor'}), 500

    

@app.route('/eliminar_usuario_proyecto/<int:usuario_id>/<int:proyecto_id>', methods=['DELETE'])
def eliminar_usuario_proyecto(usuario_id, proyecto_id):
    try:
        cursor = conexion.connection.cursor()

        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if usuario is None:
            return jsonify({'mensaje': 'Usuario no encontrado'}), 404
        elif usuario[0] != 1:
            return jsonify({'mensaje': 'El usuario no tiene permisos para realizar esta acción'}), 403

        body = request.json
        if 'usuario' not in body:
            return jsonify({'mensaje': 'El cuerpo de la solicitud debe contener el ID del usuario'}), 400

        usuario_proyecto_id = body['usuario']
        cursor.execute("SELECT 1 FROM usuarios_proyectos WHERE usuario = %s AND proyecto = %s", (usuario_proyecto_id, proyecto_id))
        if cursor.fetchone() is None:
            return jsonify({'mensaje': 'El usuario no está asignado a este proyecto'}), 400

        cursor.execute("DELETE FROM usuarios_proyectos WHERE usuario = %s", (usuario_proyecto_id,))
        conexion.connection.commit()

        cursor.close()

        return jsonify({'mensaje': 'Usuario eliminado del proyecto correctamente'})

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500


@app.route('/proyectos_usuario/<int:usuario_id>', methods=['GET'])
def proyectos_usuario(usuario_id):
    try:
        cursor = conexion.connection.cursor()

        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if usuario is None:
            return jsonify({'mensaje': 'Usuario no encontrado'}), 404

        if usuario[0] == 1:
            cursor.execute("SELECT id, nombre, descripcion, fecha_inicio FROM proyectos WHERE gerente = %s", (usuario_id,))
            proyectos = cursor.fetchall()
        else:
            cursor.execute("SELECT proyecto FROM usuarios_proyectos WHERE usuario = %s", (usuario_id,))
            proyectos_asignados = cursor.fetchall()

            proyectos = []
            for proyecto_asignado in proyectos_asignados:
                cursor.execute("SELECT id, nombre, descripcion, fecha_inicio FROM proyectos WHERE id = %s", (proyecto_asignado,))
                proyecto = cursor.fetchone()
                if proyecto:
                    proyectos.append(proyecto)

        cursor.close()

        return jsonify({'proyectos': proyectos}), 200

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500    


@app.route('/crear_historia/<int:usuario_id>', methods=['POST'])
def crear_historia(usuario_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        rol_usuario = cursor.fetchone()

        if rol_usuario and rol_usuario[0] == 1:
            body = request.json
            detalles = body.get('detalles')
            criterios = body.get('criterios')
            proyecto_id = body.get('proyecto_id')
            usuario_asignado_id = body.get('usuario_id')

            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            proyecto_existente = cursor.fetchone()

            if proyecto_existente:
                cursor.execute("SELECT 1 FROM usuarios_proyectos WHERE usuario = %s AND proyecto = %s", (usuario_asignado_id, proyecto_id))
                usuario_asignado = cursor.fetchone()

                if usuario_asignado:
                    cursor.execute("INSERT INTO historias_usuarios (detalles, criterios, proyecto, estado, usuario) VALUES (%s, %s, %s, 1, %s)", (detalles, criterios, proyecto_id, usuario_asignado_id))
                    conexion.connection.commit()

                    historia_id = cursor.lastrowid

                    hora_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("INSERT INTO update_estado_historia (historia_usuario, estado, usuario, hora_actualizacion) VALUES (%s, %s, %s, %s)",
                                   (historia_id, 1, usuario_id, hora_actualizacion))
                    conexion.connection.commit()

                    return jsonify({'mensaje': 'Historia de usuario creada correctamente'})
                else:
                    return jsonify({'mensaje': 'El usuario asignado no está asignado a este proyecto'}), 403
            else:
                return jsonify({'mensaje': 'El proyecto especificado no existe'}), 404
        else:
            return jsonify({'mensaje': 'El usuario no tiene permisos para crear historias de usuario'}), 403
    except Exception as ex:
        return jsonify({'mensaje': 'Error en el servidor'}), 500


@app.route('/editar_historia/<int:usuario_id>/<int:historia_id>', methods=['PUT'])
def editar_historia(usuario_id, historia_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if usuario is None:
            return jsonify({'mensaje': 'Usuario no encontrado'}), 404
        elif usuario[0] != 1:
            return jsonify({'mensaje': 'El usuario no tiene permisos para editar historias de usuario'}), 403

        detalles = request.json.get('detalles')
        criterios = request.json.get('criterios')


        cursor.execute("UPDATE historias_usuarios SET detalles = %s, criterios = %s WHERE id = %s", (detalles, criterios, historia_id))
        conexion.connection.commit()

        cursor.close()

        return jsonify({'mensaje': 'Historia de usuario actualizada correctamente'})

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500


@app.route('/eliminar_historia_usuario/<int:usuario_id>/<int:historia_id>', methods=['DELETE'])
def eliminar_historia_usuario(usuario_id, historia_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        rol_usuario = cursor.fetchone()

        if rol_usuario and rol_usuario[0] == 1:
            cursor.execute("SELECT id FROM historias_usuarios WHERE id = %s", (historia_id,))
            historia_existente = cursor.fetchone()

            if historia_existente:
                cursor.execute("DELETE FROM historias_usuarios WHERE id = %s", (historia_id,))
                conexion.connection.commit()

                cursor.close()

                return jsonify({'mensaje': 'Historia de usuario eliminada correctamente'})
            else:
                return jsonify({'mensaje': 'La historia de usuario especificada no existe'}), 404
        else:
            return jsonify({'mensaje': 'El usuario no tiene permisos para eliminar historias de usuario'}), 403

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500
    

from flask import jsonify

@app.route('/crear_tarea/<int:usuario_id>/<int:historia_id>', methods=['POST'])
def crear_tarea(usuario_id, historia_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        rol_usuario = cursor.fetchone()

        if rol_usuario and (rol_usuario[0] == 1 or usuario_id == historia_id):
            data = request.json
            descripcion = data.get('descripcion')

            if not descripcion:
                return jsonify({'mensaje': 'La descripción de la tarea es requerida'}), 400

            cursor.execute("INSERT INTO tareas (descripcion, estado, historia_usuario, usuarios_id) VALUES (%s, %s, %s, %s)",
                           (descripcion, 1, historia_id, usuario_id))
            conexion.connection.commit()
            tarea_id = cursor.lastrowid

            hora_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO update_estado_tarea (tarea, estado, usuario, hora_actualizacion) VALUES (%s, %s, %s, %s)",
                           (tarea_id, 1, usuario_id, hora_actualizacion))
            conexion.connection.commit()

            cursor.close()

            return jsonify({'mensaje': 'Tarea creada correctamente'})
        else:
            return jsonify({'mensaje': 'No tienes permisos para crear esta tarea'}), 403

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500



@app.route('/editar_tarea/<int:tarea_id>', methods=['PUT'])
def editar_tarea(tarea_id):
    try:
        datos_tarea = request.json
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM tareas WHERE id = %s", (tarea_id,))
        tarea_existente = cursor.fetchone()
        if tarea_existente is None:
            return jsonify({'mensaje': 'La tarea no existe'}), 404

        cursor.execute("UPDATE tareas SET descripcion = %s WHERE id = %s", (datos_tarea['descripcion'], tarea_id))
        conexion.connection.commit()
        
        return jsonify({'mensaje': 'Tarea actualizada correctamente'}), 200
    
    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500
    

@app.route('/eliminar_tarea/<int:tarea_id>', methods=['DELETE'])
def eliminar_tarea(tarea_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM tareas WHERE id = %s", (tarea_id,))
        tarea_existente = cursor.fetchone()
        if tarea_existente is None:
            return jsonify({'mensaje': 'La tarea no existe'}), 404
        
        cursor.execute("DELETE FROM tareas WHERE id = %s", (tarea_id,))
        conexion.connection.commit()
        
        return jsonify({'mensaje': 'Tarea eliminada correctamente'}), 200
    
    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500
        

@app.route('/actualizar_estado_tarea/<int:tarea_id>', methods=['PUT'])
def actualizar_estado_tarea(tarea_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM tareas WHERE id = %s", (tarea_id,))
        tarea_existente = cursor.fetchone()

        if tarea_existente:
            cursor.execute("SELECT estado FROM update_estado_tarea WHERE tarea = %s ORDER BY hora_actualizacion DESC LIMIT 1", (tarea_id,))
            ultimo_estado = cursor.fetchone()

            if ultimo_estado:
                nuevo_estado = ultimo_estado[0] + 1 if ultimo_estado[0] < 3 else ultimo_estado[0]

                cursor.execute("UPDATE tareas SET estado = %s WHERE id = %s", (nuevo_estado, tarea_id))
                conexion.connection.commit()

                hora_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO update_estado_tarea (tarea, estado, usuario, hora_actualizacion) VALUES (%s, %s, %s, %s)",
                               (tarea_id, nuevo_estado, tarea_existente[4], hora_actualizacion))
                conexion.connection.commit()

                cursor.close()

                return jsonify({'mensaje': f'Estado de la tarea actualizado correctamente a {nuevo_estado}'}), 200
            else:
                return jsonify({'mensaje': 'No se encontraron estados para esta tarea'}), 404
        else:
            return jsonify({'mensaje': 'La tarea no existe'}), 404

    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500
    

@app.route('/actualizar_estado_historia/<int:usuario_id>/<int:historia_usuario_id>', methods=['POST'])
def actualizar_estado_historia(usuario_id, historia_usuario_id):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        rol_usuario = cursor.fetchone()

        if rol_usuario and rol_usuario[0] == 1:
            cursor.execute("SELECT estado FROM tareas WHERE historia_usuario = %s", (historia_usuario_id,))
            estados_tareas = cursor.fetchall()

            if estados_tareas:
                if all(estado[0] == 1 for estado in estados_tareas):
                    nuevo_estado = 1
                elif any(estado[0] == 2 for estado in estados_tareas):
                    nuevo_estado = 2
                else:
                    nuevo_estado = 3

                cursor.execute("UPDATE historias_usuarios SET estado = %s WHERE id = %s", (nuevo_estado, historia_usuario_id))
                conexion.connection.commit()


                hora_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO update_estado_historia (historia_usuario, estado, usuario, hora_actualizacion) VALUES (%s, %s, %s, %s)",
                               (historia_usuario_id, nuevo_estado, usuario_id, hora_actualizacion))
                conexion.connection.commit()

                return jsonify({'mensaje': f'Estado de la historia de usuario actualizado correctamente a {nuevo_estado}'}), 200
            else:
                return jsonify({'mensaje': 'No hay tareas asociadas a esta historia de usuario'}), 404
        else:
            return jsonify({'mensaje': 'No tienes permisos para actualizar el estado de esta historia de usuario'}), 403
    except Exception as e:
        return jsonify({'mensaje': str(e)}), 500  



if __name__ == '__main__':
    app.config.from_object(config['development'])
    app.run()