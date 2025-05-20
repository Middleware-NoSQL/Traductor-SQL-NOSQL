from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def create_auth_blueprint(user_model):
    """
    Crea y configura el blueprint de autenticación.
    
    Args:
        user_model: Instancia del modelo de usuario
    """
    auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
    
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """
        Endpoint para registrar un nuevo usuario.
        """
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            required_fields = ['username', 'email', 'password']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"error": f"El campo {field} es requerido"}), 400
            
            # Validar longitud de contraseña
            if len(data['password']) < 6:
                return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
            
            # Crear usuario (por defecto como 'user')
            result = user_model.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                role='user'
            )
            
            if 'error' in result:
                return jsonify(result), 400
            
            logger.info(f"Usuario registrado: {data['username']}")
            return jsonify({
                "message": "Usuario registrado exitosamente",
                "user": result
            }), 201
            
        except Exception as e:
            logger.error(f"Error en registro: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
    
    @auth_bp.route('/login', methods=['POST'])
    def login():
        """
        Endpoint para iniciar sesión.
        """
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            if not data.get('username') or not data.get('password'):
                return jsonify({"error": "Usuario y contraseña son requeridos"}), 400
            
            # Autenticar usuario
            user = user_model.authenticate_user(data['username'], data['password'])
            
            if not user:
                return jsonify({"error": "Credenciales inválidas"}), 401
            
            # Crear tokens JWT
            additional_claims = {
                "role": user["role"],
                "permissions": user["permissions"]
            }
            
            access_token = create_access_token(
                identity=user["_id"],
                additional_claims=additional_claims,
                expires_delta=timedelta(hours=24)
            )
            
            refresh_token = create_refresh_token(
                identity=user["_id"],
                expires_delta=timedelta(days=30)
            )
            
            logger.info(f"Usuario autenticado: {user['username']}")
            return jsonify({
                "message": "Inicio de sesión exitoso",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user["_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "permissions": user["permissions"]
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
    
    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """
        Endpoint para renovar token de acceso.
        """
        try:
            user_id = get_jwt_identity()
            user = user_model.get_user_by_id(user_id)
            
            if not user:
                return jsonify({"error": "Usuario no encontrado"}), 404
            
            # Crear nuevo token de acceso
            additional_claims = {
                "role": user["role"],
                "permissions": user["permissions"]
            }
            
            new_token = create_access_token(
                identity=user_id,
                additional_claims=additional_claims,
                expires_delta=timedelta(hours=24)
            )
            
            return jsonify({"access_token": new_token}), 200
            
        except Exception as e:
            logger.error(f"Error en refresh: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
    
    @auth_bp.route('/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """
        Endpoint para obtener el perfil del usuario actual.
        """
        try:
            user_id = get_jwt_identity()
            user = user_model.get_user_by_id(user_id)
            
            if not user:
                return jsonify({"error": "Usuario no encontrado"}), 404
            
            return jsonify({"user": user}), 200
            
        except Exception as e:
            logger.error(f"Error al obtener perfil: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
    
    return auth_bp