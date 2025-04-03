class MongoShellQueryGenerator:
    """
    Clase encargada de generar consultas ejecutables para la shell de MongoDB
    a partir de las operaciones generadas por el traductor SQL-MongoDB.
    """
    
    @staticmethod
    def generate_shell_query(collection_name, mongo_query):
        """
        Genera una consulta ejecutable para la shell de MongoDB.
        
        :param collection_name: Nombre de la colección (str)
        :param mongo_query: Consulta en formato MongoDB (dict)
        :return: String con la consulta ejecutable
        """
        operation = mongo_query.get("operation")
        
        if not operation:
            return "// No se pudo generar la consulta para la shell de MongoDB"
        
        if operation == "find":
            return MongoShellQueryGenerator._generate_find(collection_name, mongo_query)
        elif operation == "aggregate":
            return MongoShellQueryGenerator._generate_aggregate(collection_name, mongo_query)
        elif operation == "insert":
            return MongoShellQueryGenerator._generate_insert(collection_name, mongo_query)
        elif operation == "update":
            return MongoShellQueryGenerator._generate_update(collection_name, mongo_query)
        elif operation == "delete":
            return MongoShellQueryGenerator._generate_delete(collection_name, mongo_query)
        else:
            return f"// Operación '{operation}' no soportada para la shell de MongoDB"
    
    @staticmethod
    def _generate_find(collection_name, mongo_query):
        """Genera una consulta find() para la shell de MongoDB."""
        query_filter = mongo_query.get("query", {})
        projection = mongo_query.get("projection", None)
        sort = mongo_query.get("sort", None)
        limit = mongo_query.get("limit", None)
        
        # Construir consulta base
        query_parts = [
            f"db.{collection_name}.find(",
            f"  {MongoShellQueryGenerator._format_json(query_filter)}"
        ]
        
        # Añadir proyección si existe
        if projection:
            query_parts.append(f", {MongoShellQueryGenerator._format_json(projection)}")
        
        query_parts.append(")")
        
        # Añadir ordenamiento si existe
        if sort:
            sort_str = MongoShellQueryGenerator._format_json(sort)
            query_parts.append(f".sort({sort_str})")
        
        # Añadir límite si existe
        if limit is not None:
            query_parts.append(f".limit({limit})")
        
        # Añadir pretty() para mejor visualización
        query_parts.append(".pretty()")
        
        return "".join(query_parts)
    
    @staticmethod
    def _generate_aggregate(collection_name, mongo_query):
        """Genera una consulta aggregate() para la shell de MongoDB."""
        pipeline = mongo_query.get("pipeline", [])
        
        # Formatear pipeline para que sea legible
        formatted_pipeline = MongoShellQueryGenerator._format_json_array(pipeline)
        
        return f"db.{collection_name}.aggregate({formatted_pipeline}).pretty()"
    
    @staticmethod
    def _generate_insert(collection_name, mongo_query):
        """Genera una consulta insertOne() para la shell de MongoDB."""
        document = mongo_query.get("document", {})
        
        # Formatear documento para que sea legible
        formatted_doc = MongoShellQueryGenerator._format_json(document)
        
        return f"db.{collection_name}.insertOne({formatted_doc})"
    
    @staticmethod
    def _generate_update(collection_name, mongo_query):
        """Genera una consulta updateMany() para la shell de MongoDB."""
        query_data = mongo_query.get("query", {})
        
        if not query_data or not isinstance(query_data, dict):
            return f"// Error: Formato de consulta update inválido"
        
        filter_query = query_data.get("query", {})
        update_query = query_data.get("update", {})
        
        # Formatear query y update para que sean legibles
        formatted_filter = MongoShellQueryGenerator._format_json(filter_query)
        formatted_update = MongoShellQueryGenerator._format_json(update_query)
        
        return f"db.{collection_name}.updateMany({formatted_filter}, {formatted_update})"
    
    @staticmethod
    def _generate_delete(collection_name, mongo_query):
        """Genera una consulta deleteMany() para la shell de MongoDB."""
        query_filter = mongo_query.get("query", {})
        
        # Formatear filtro para que sea legible
        formatted_filter = MongoShellQueryGenerator._format_json(query_filter)
        
        return f"db.{collection_name}.deleteMany({formatted_filter})"
    
    @staticmethod
    def _format_json(obj, indent=2, current_indent=2):
        """
        Formatea un objeto JSON (diccionario) para que sea legible en la consola de MongoDB.
        Maneja la indentación y formato específico de MongoDB.
        """
        if not obj:
            return "{}"
        
        if not isinstance(obj, dict):
            return str(obj)
        
        # Si es un diccionario vacío, devuelve {}
        if len(obj) == 0:
            return "{}"
        
        # Iniciar formato
        result = "{\n"
        
        # Procesar cada par clave-valor
        items = list(obj.items())
        for i, (key, value) in enumerate(items):
            # Añadir indentación
            result += " " * current_indent
            
            # Formatear clave
            if key.startswith("$"):
                # Operadores MongoDB ($eq, $gt, etc.)
                result += f"{key}: "
            else:
                # Campos normales
                result += f'"{key}": '
            
            # Formatear valor según su tipo
            if isinstance(value, dict):
                # Recursivamente formatear diccionarios anidados
                result += MongoShellQueryGenerator._format_json(value, indent, current_indent + indent)
            elif isinstance(value, list):
                # Formatear arrays
                result += MongoShellQueryGenerator._format_json_array(value, indent, current_indent + indent)
            elif isinstance(value, str):
                # Cadenas de texto
                if key.startswith("$") and value.startswith("$"):
                    # Referencias a campos ($field)
                    result += f'"{value}"'
                else:
                    result += f'"{value}"'
            elif value is None:
                # Valores nulos
                result += "null"
            else:
                # Otros valores (números, booleanos)
                result += str(value)
            
            # Añadir coma si no es el último elemento
            if i < len(items) - 1:
                result += ","
            
            result += "\n"
        
        # Cerrar el objeto con indentación adecuada
        result += " " * (current_indent - indent) + "}"
        
        return result
    
    @staticmethod
    def _format_json_array(arr, indent=2, current_indent=2):
        """
        Formatea un array JSON para que sea legible en la consola de MongoDB.
        """
        if not arr:
            return "[]"
        
        # Iniciar formato
        result = "[\n"
        
        # Procesar cada elemento
        for i, item in enumerate(arr):
            # Añadir indentación
            result += " " * current_indent
            
            # Formatear el elemento según su tipo
            if isinstance(item, dict):
                result += MongoShellQueryGenerator._format_json(item, indent, current_indent + indent)
            elif isinstance(item, list):
                result += MongoShellQueryGenerator._format_json_array(item, indent, current_indent + indent)
            elif isinstance(item, str):
                result += f'"{item}"'
            elif item is None:
                result += "null"
            else:
                result += str(item)
            
            # Añadir coma si no es el último elemento
            if i < len(arr) - 1:
                result += ","
            
            result += "\n"
        
        # Cerrar el array con indentación adecuada
        result += " " * (current_indent - indent) + "]"
        
        return result