from flask import Flask, request, jsonify
from app.parser import SQLParser
from app.translator import SQLToMongoDBTranslator
from app.connector import MongoDBConnector
from app.mongo_shell import MongoShellQueryGenerator
import traceback
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Configuración de conexión MongoDB
MONGO_URI = "mongodb://localhost:27017/"

# Inicializar el conector MongoDB usando el patrón singleton
try:
    # Usar test_db para desarrollo/pruebas iniciales
    mongo_connector = MongoDBConnector.get_instance(MONGO_URI, "test_db")
    print("Conector MongoDB inicializado correctamente")
except Exception as e:
    print(f"Error al inicializar el conector MongoDB: {e}")
    print(traceback.format_exc())

@app.route('/databases', methods=['GET'])
def get_databases():
    """
    Endpoint para obtener las bases de datos disponibles.
    """
    try:
        # Usar el singleton
        databases = mongo_connector.get_available_databases()
        return jsonify({"databases": databases})
    except Exception as e:
        print(f"Error al obtener bases de datos: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/database/<database_name>/collections', methods=['GET'])
def get_collections(database_name):
    """
    Endpoint para obtener las colecciones de una base de datos.
    """
    try:
        # Usar el singleton
        collections = mongo_connector.get_collections(database_name)
        return jsonify({"collections": collections})
    except Exception as e:
        print(f"Error al obtener colecciones: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/connect', methods=['POST'])
def connect_database():
    """
    Endpoint para conectarse a una base de datos específica.
    """
    try:
        data = request.get_json()
        if not data or 'database' not in data:
            return jsonify({"error": "Se requiere el nombre de la base de datos"}), 400
        
        database_name = data['database']
        # Usar el singleton
        collections = mongo_connector.set_database(database_name)
        
        return jsonify({
            "message": f"Conectado a la base de datos {database_name}",
            "collections": collections
        })
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/translate', methods=['POST'])
def translate_sql_to_mongodb():
    """
    Endpoint para traducir y ejecutar consultas SQL en MongoDB.
    """
    try:
        # Obtener la consulta SQL del JSON recibido
        data = request.get_json()
        
        # Verificar si se proporciona una base de datos específica para esta consulta
        if 'database' in data:
            database_name = data['database']
            mongo_connector.set_database(database_name)
            print(f"Base de datos seleccionada para esta consulta: {database_name}")
        
        if not data or 'query' not in data:
            print("Error: No se proporcionó la consulta SQL en el JSON")
            return jsonify({"error": "Se requiere una consulta SQL en el campo 'query'"}), 400
        
        sql_query = data['query']
        print(f"Consulta SQL recibida: {sql_query}")
        
        # Parsear la consulta SQL
        parser = SQLParser(sql_query)
        
        # Obtener el nombre de la tabla/colección
        collection_name = parser.get_table_name()
        print(f"Nombre de colección detectado: {collection_name}")
        
        if not collection_name:
            print("Error: No se pudo determinar el nombre de la colección")
            return jsonify({"error": "No se pudo determinar el nombre de la colección"}), 400
        
        # Traducir la consulta a formato MongoDB
        translator = SQLToMongoDBTranslator(parser)
        mongo_query = translator.translate()
        print(f"Consulta MongoDB generada: {mongo_query}")
        
        # Ejecutar la consulta en MongoDB usando el singleton
        result = mongo_connector.execute_query(collection_name, mongo_query)
        print(f"Resultado de la consulta: {result}")
        
        return jsonify(result)
    except ValueError as e:
        print(f"Error de valor: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# Añadir esta nueva ruta después del endpoint '/translate'
@app.route('/generate-shell-query', methods=['POST'])
def generate_shell_query():
    """
    Endpoint para generar una consulta ejecutable para la shell de MongoDB.
    """
    try:
        # Obtener la consulta SQL del JSON recibido
        data = request.get_json()
        
        if not data or 'query' not in data:
            print("Error: No se proporcionó la consulta SQL en el JSON")
            return jsonify({"error": "Se requiere una consulta SQL en el campo 'query'"}), 400
        
        # Verificar si se proporciona una base de datos específica para esta consulta
        if 'database' in data:
            database_name = data['database']
            mongo_connector.set_database(database_name)
            print(f"Base de datos seleccionada para esta consulta: {database_name}")
        
        sql_query = data['query']
        print(f"Consulta SQL recibida para generar query shell: {sql_query}")
        
        # Parsear la consulta SQL
        parser = SQLParser(sql_query)
        
        # Obtener el nombre de la tabla/colección
        collection_name = parser.get_table_name()
        print(f"Nombre de colección detectado: {collection_name}")
        
        if not collection_name:
            print("Error: No se pudo determinar el nombre de la colección")
            return jsonify({"error": "No se pudo determinar el nombre de la colección"}), 400
        
        # Traducir la consulta a formato MongoDB
        translator = SQLToMongoDBTranslator(parser)
        mongo_query = translator.translate()
        print(f"Consulta MongoDB generada: {mongo_query}")
        
        # Generar la consulta para la shell de MongoDB
        shell_query = MongoShellQueryGenerator.generate_shell_query(collection_name, mongo_query)
        print(f"Consulta para la shell de MongoDB generada: {shell_query}")
        
        return jsonify({"shell_query": shell_query})
    except ValueError as e:
        print(f"Error de valor: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)