from bson import ObjectId
from pymongo import MongoClient
import time

# Variable global para el singleton
_instance = None

class MongoDBConnector:
    @staticmethod
    def get_instance(uri, database_name=None):
        """
        Método estático para obtener la instancia singleton del conector.
        """
        global _instance
        if _instance is None:
            _instance = MongoDBConnector(uri, database_name)
        return _instance
    
    def __init__(self, uri, database_name=None):
        """
        Inicializa el conector con MongoDB.
        :param uri: URI de conexión a MongoDB.
        :param database_name: Nombre de la base de datos (opcional).
        """
        try:
            print(f"Iniciando conexión a MongoDB: {uri}")
            # No cerrar automáticamente la conexión
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.uri = uri
            
            # Verificar conexión
            self.client.admin.command('ping')
            print("Conexión exitosa a MongoDB")
            
            # Listar bases de datos disponibles
            self.available_databases = self.client.list_database_names()
            print(f"Bases de datos disponibles: {self.available_databases}")
            
            # Establecer la base de datos si se proporcionó
            if database_name:
                self.set_database(database_name)
            else:
                self.db = None
                print("No se ha seleccionado ninguna base de datos. Use set_database() para seleccionar una.")
                
        except Exception as e:
            print(f"Error al conectar a MongoDB: {e}")
            import traceback
            print(traceback.format_exc())
            raise
    
    def set_database(self, database_name):
        """
        Establece la base de datos a utilizar.
        :param database_name: Nombre de la base de datos.
        :return: Lista de colecciones disponibles en la base de datos.
        """
        try:
            self.db = self.client[database_name]
            self.database_name = database_name
            
            # Listar colecciones disponibles
            collections = self.db.list_collection_names()
            print(f"Conexión establecida con base de datos: {database_name}")
            print(f"Colecciones disponibles en {database_name}: {collections}")
            
            return collections
        except Exception as e:
            print(f"Error al seleccionar la base de datos {database_name}: {e}")
            import traceback
            print(traceback.format_exc())
            raise
    
    def get_available_databases(self):
        """
        Obtiene la lista de bases de datos disponibles.
        :return: Lista de bases de datos.
        """
        try:
            # Actualizar la lista de bases de datos
            self.available_databases = self.client.list_database_names()
            return self.available_databases
        except Exception as e:
            print(f"Error al obtener bases de datos disponibles: {e}")
            self._try_reconnect()
            # Intentar nuevamente después de reconectar
            return self.client.list_database_names() if hasattr(self, 'client') else []
    
    def _try_reconnect(self):
        """
        Intenta reconectar al servidor MongoDB.
        """
        try:
            print("Intentando reconectar a MongoDB...")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            print("Reconexión exitosa")
            
            # Si había una base de datos seleccionada, volver a seleccionarla
            if hasattr(self, 'database_name') and self.database_name:
                self.set_database(self.database_name)
        except Exception as e:
            print(f"Error al reconectar: {e}")
    
    def get_collections(self, database_name=None):
        """
        Obtiene las colecciones disponibles en una base de datos.
        :param database_name: Nombre de la base de datos (opcional, usa la actual si no se proporciona).
        :return: Lista de colecciones.
        """
        try:
            if database_name:
                db = self.client[database_name]
            elif hasattr(self, 'db') and self.db:
                db = self.db
            else:
                return []
            
            return db.list_collection_names()
        except Exception as e:
            print(f"Error al obtener colecciones: {e}")
            self._try_reconnect()
            # Intentar nuevamente después de reconectar
            try:
                if database_name:
                    return self.client[database_name].list_collection_names()
                elif hasattr(self, 'db') and self.db:
                    return self.db.list_collection_names()
            except:
                pass
            return []

    def execute_query(self, collection_name, query):
        """
        Ejecuta una consulta en MongoDB.
        :param collection_name: Nombre de la colección.
        :param query: Consulta en formato MongoDB.
        :return: Resultado de la consulta.
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not hasattr(self, 'db') or self.db is None:
                    raise ValueError("No se ha seleccionado ninguna base de datos. Use set_database() primero.")
                    
                # Normalizar nombre de colección (MongoDB distingue mayúsculas/minúsculas)
                collection_name = collection_name.lower()
                print(f"Ejecutando consulta en colección: {collection_name}")
                print(f"Consulta a ejecutar: {query}")
                
                collection = self.db[collection_name]
                operation = query.get("operation")
                print(f"Operación a realizar: {operation}")
                
                if operation == "find":
                    mongo_query = query.get("query", {})
                    projection = query.get("projection", None)
                    sort = query.get("sort", None)
                    limit = query.get("limit", None)
                    
                    print(f"Consulta de búsqueda: {mongo_query}")
                    print(f"Proyección: {projection}")
                    print(f"Ordenamiento: {sort}")
                    print(f"Límite: {limit}")
                    
                    # Preparar el cursor
                    cursor = collection.find(mongo_query, projection)
                    
                    # Aplicar ordenamiento si existe
                    if sort:
                        cursor = cursor.sort(list(sort.items()))
                    
                    # Aplicar límite si existe
                    if limit is not None:
                        cursor = cursor.limit(limit)
                    
                    # Ejecutar la consulta
                    results = list(cursor)
                    print(f"Resultados encontrados: {len(results)}")
                    
                    # Convertir ObjectId a string para serialización JSON
                    for result in results:
                        if "_id" in result:
                            result["_id"] = str(result["_id"])
                    
                    return results
                    
                elif operation == "aggregate":
                    pipeline = query.get("pipeline", [])
                    print(f"Pipeline de agregación: {pipeline}")
                    
                    # Ejecutar la consulta de agregación
                    results = list(collection.aggregate(pipeline))
                    print(f"Resultados de agregación encontrados: {len(results)}")
                    
                    # Convertir ObjectId a string para serialización JSON
                    for result in results:
                        if "_id" in result and isinstance(result["_id"], dict):
                            # Si _id es un documento (ej. en GROUP BY)
                            result["_id"] = str(result["_id"])
                        elif "_id" in result:
                            result["_id"] = str(result["_id"])
                    
                    return results
                    
                elif operation == "insert":
                    document = query.get("document")
                    print(f"Documento a insertar: {document}")
                    result = collection.insert_one(document)
                    return {"inserted_id": str(result.inserted_id)}
                    
                elif operation == "update":
                    update_query = query.get("query")
                    if not isinstance(update_query, dict) or "query" not in update_query or "update" not in update_query:
                        print("Error: Formato inválido para consulta update. Se espera {'query': {...}, 'update': {...}}")
                        print(f"Consulta recibida: {update_query}")
                        raise ValueError("Formato inválido para consulta update")
                    
                    print(f"Consulta de actualización: filtro={update_query['query']}, valores={update_query['update']}")
                    result = collection.update_many(update_query["query"], update_query["update"])
                    return {"modified_count": result.modified_count, "matched_count": result.matched_count}
                    
                elif operation == "delete":
                    delete_query = query.get("query")
                    print(f"Consulta de eliminación: {delete_query}")
                    result = collection.delete_many(delete_query)
                    return {"deleted_count": result.deleted_count}
                    
                # Operaciones de creación y alteración de colecciones/índices
                elif operation == "create_collection":
                    collection_name = query.get("collection_name")
                    options = query.get("options", {})
                    print(f"Creando colección: {collection_name}")
                    self.db.create_collection(collection_name, **options)
                    return {"created": True, "collection_name": collection_name}
                    
                elif operation == "create_index":
                    index_spec = query.get("index_spec")
                    options = query.get("options", {})
                    print(f"Creando índice en {collection_name}: {index_spec}")
                    result = collection.create_index(index_spec, **options)
                    return {"created": True, "index_name": result}
                    
                elif operation == "drop_collection":
                    print(f"Eliminando colección: {collection_name}")
                    collection.drop()
                    return {"dropped": True, "collection_name": collection_name}
                    
                elif operation == "drop_index":
                    index_name = query.get("index_name")
                    print(f"Eliminando índice {index_name} de {collection_name}")
                    collection.drop_index(index_name)
                    return {"dropped": True, "index_name": index_name}
                    
                # Operaciones específicas de MongoDB
                elif operation == "count":
                    mongo_query = query.get("query", {})
                    print(f"Contando documentos con filtro: {mongo_query}")
                    count = collection.count_documents(mongo_query)
                    return {"count": count}
                    
                elif operation == "distinct":
                    field = query.get("field")
                    mongo_query = query.get("query", {})
                    print(f"Obteniendo valores distintos de {field} con filtro: {mongo_query}")
                    values = collection.distinct(field, mongo_query)
                    return {"distinct_values": values}
                    
                elif operation == "bulk_write":
                    operations = query.get("operations", [])
                    options = query.get("options", {})
                    print(f"Ejecutando operaciones bulk_write: {len(operations)} operaciones")
                    result = collection.bulk_write(operations, **options)
                    return {
                        "inserted_count": result.inserted_count,
                        "modified_count": result.modified_count,
                        "deleted_count": result.deleted_count,
                        "upserted_count": result.upserted_count
                    }
                
                raise ValueError(f"Operación no soportada: {operation}")
                
            except Exception as e:
                print(f"Error al ejecutar consulta (intento {retry_count+1}): {e}")
                retry_count += 1
                
                if "MongoClient after close" in str(e):
                    print("Detectado error de cliente cerrado. Intentando reconectar...")
                    self._try_reconnect()
                    # Esperar un momento antes de reintentar
                    time.sleep(1)
                elif retry_count >= max_retries:
                    import traceback
                    print(traceback.format_exc())
                    raise
                else:
                    # Esperar un poco antes de reintentar para otros errores
                    time.sleep(0.5)
        
        raise Exception("Se excedió el número máximo de intentos de consulta")