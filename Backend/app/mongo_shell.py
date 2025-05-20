class MongoShellQueryGenerator:
    """
    Clase encargada de generar consultas ejecutables para la shell de MongoDB
    a partir de las operaciones generadas por el traductor SQL-MongoDB.
    """
    
    @staticmethod
    def generate_shell_query(collection_name, mongo_query):
        """
        Genera una consulta ejecutable para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: String con la consulta ejecutable
        """
        operation = mongo_query.get("operation")
        
        if not operation:
            return "// No se pudo generar la consulta para la shell de MongoDB"
        
        # Seleccionar el método adecuado según la operación
        generators = {
            "find": MongoShellQueryGenerator._generate_find,
            "aggregate": MongoShellQueryGenerator._generate_aggregate,
            "insert": MongoShellQueryGenerator._generate_insert,
            "update": MongoShellQueryGenerator._generate_update,
            "delete": MongoShellQueryGenerator._generate_delete,
            "create_collection": MongoShellQueryGenerator._generate_create_collection,
            "drop_collection": MongoShellQueryGenerator._generate_drop_collection
        }
        
        if operation in generators:
            return generators[operation](collection_name, mongo_query)
        else:
            return f"// Operación '{operation}' no soportada para la shell de MongoDB"
    
    @staticmethod
    def _generate_find(collection_name, mongo_query):
        """
        Genera una consulta find() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        # Extraer componentes de la consulta
        query_filter = mongo_query.get("query", {})
        projection = mongo_query.get("projection", None)
        sort = mongo_query.get("sort", None)
        limit = mongo_query.get("limit", None)
        skip = mongo_query.get("skip", None)
        
        # Construir la consulta básica
        query_parts = []
        
        # Parte principal del find()
        if projection:
            query_parts.append(
                f"db.{collection_name}.find(\n" +
                f"  {MongoShellQueryGenerator._format_json(query_filter)},\n" +
                f"  {MongoShellQueryGenerator._format_json(projection)}\n" +
                f")"
            )
        else:
            query_parts.append(
                f"db.{collection_name}.find(\n" +
                f"  {MongoShellQueryGenerator._format_json(query_filter)}\n" +
                f")"
            )
        
        # Añadir los métodos de cursor en orden adecuado
        if sort:
            query_parts[0] += ".sort(" + MongoShellQueryGenerator._format_json(sort) + ")"
        
        if skip:
            query_parts[0] += f".skip({skip})"
        
        if limit is not None:
            query_parts[0] += f".limit({limit})"
        
        # Añadir pretty() para mejor visualización
        query_parts[0] += ".pretty()"
        
        # Añadir comentario explicativo
        query = "// Consulta equivalente a SELECT en MongoDB\n" + query_parts[0]
        return query
    
    @staticmethod
    def _generate_aggregate(collection_name, mongo_query):
        """
        Genera una consulta aggregate() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        pipeline = mongo_query.get("pipeline", [])
        
        # Formatear el pipeline para mejor legibilidad
        formatted_pipeline = MongoShellQueryGenerator._format_json_array(pipeline, indent=2)
        
        # Construir la consulta completa
        query = "// Consulta de agregación en MongoDB\n" + \
                f"db.{collection_name}.aggregate(\n" + \
                f"{formatted_pipeline}\n" + \
                ").pretty()"
        
        return query
    
    @staticmethod
    def _generate_insert(collection_name, mongo_query):
        """
        Genera una consulta insertOne() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        document = mongo_query.get("document", {})
        
        # Formatear el documento para mejor legibilidad
        formatted_doc = MongoShellQueryGenerator._format_json(document, indent=2)
        
        # Construir la consulta completa
        query = "// Inserción de documento en MongoDB\n" + \
                f"db.{collection_name}.insertOne(\n" + \
                f"{formatted_doc}\n" + \
                ")"
        
        return query
    
    @staticmethod
    def _generate_update(collection_name, mongo_query):
        """
        Genera una consulta updateMany() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        query_data = mongo_query.get("query", {})
        
        if not query_data or not isinstance(query_data, dict):
            return "// Error: Formato de consulta update inválido"
        
        filter_query = query_data.get("query", {})
        update_query = query_data.get("update", {})
        
        # Formatear las partes para mejor legibilidad
        formatted_filter = MongoShellQueryGenerator._format_json(filter_query, indent=2)
        formatted_update = MongoShellQueryGenerator._format_json(update_query, indent=2)
        
        # Construir la consulta completa
        query = "// Actualización de documentos en MongoDB\n" + \
                f"db.{collection_name}.updateMany(\n" + \
                f"{formatted_filter},\n" + \
                f"{formatted_update}\n" + \
                ")"
        
        return query
    
    @staticmethod
    def _generate_delete(collection_name, mongo_query):
        """
        Genera una consulta deleteMany() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        query_filter = mongo_query.get("query", {})
        
        # Formatear el filtro para mejor legibilidad
        formatted_filter = MongoShellQueryGenerator._format_json(query_filter, indent=2)
        
        # Construir la consulta completa
        query = "// Eliminación de documentos en MongoDB\n" + \
                f"db.{collection_name}.deleteMany(\n" + \
                f"{formatted_filter}\n" + \
                ")"
        
        return query
    
    @staticmethod
    def _generate_create_collection(collection_name, mongo_query):
        """
        Genera una consulta createCollection() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        options = mongo_query.get("options", {})
        
        # Formatear opciones para mejor legibilidad
        formatted_options = MongoShellQueryGenerator._format_json(options, indent=2)
        
        # Construir la consulta completa
        if options:
            query = "// Creación de colección en MongoDB\n" + \
                    f"db.createCollection(\n" + \
                    f"  \"{collection_name}\",\n" + \
                    f"  {formatted_options}\n" + \
                    ")"
        else:
            query = "// Creación de colección en MongoDB\n" + \
                    f"db.createCollection(\"{collection_name}\")"
        
        return query
    
    @staticmethod
    def _generate_drop_collection(collection_name, mongo_query):
        """
        Genera una consulta drop() para la shell de MongoDB.
        
        Args:
            collection_name (str): Nombre de la colección
            mongo_query (dict): Consulta en formato MongoDB
            
        Returns:
            str: Consulta para la shell de MongoDB
        """
        return "// Eliminación de colección en MongoDB\n" + \
               f"db.{collection_name}.drop()"
    
    @staticmethod
    def _format_json(obj, indent=2, current_indent=2):
        """
        Formatea un objeto JSON (diccionario) para que sea legible en la consola de MongoDB.
        
        Args:
            obj: Objeto a formatear
            indent (int): Cantidad de espacios para indentación
            current_indent (int): Indentación actual
            
        Returns:
            str: JSON formateado
        """
        if obj is None:
            return "null"
        
        if not isinstance(obj, dict):
            if isinstance(obj, str):
                return f'"{obj}"'
            elif isinstance(obj, bool):
                return "true" if obj else "false"
            else:
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
                result += f'"{value}"'
            elif value is None:
                # Valores nulos
                result += "null"
            else:
                # Otros valores (números, booleanos)
                if isinstance(value, bool):
                    result += "true" if value else "false"
                else:
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
        Formatea un array JSON para la shell de MongoDB.
        
        Args:
            arr: Array a formatear
            indent (int): Cantidad de espacios para indentación
            current_indent (int): Indentación actual
            
        Returns:
            str: Array formateado
        """
        if arr is None:
            return "null"
        
        if not isinstance(arr, list):
            return str(arr)
        
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
            elif isinstance(item, bool):
                result += "true" if item else "false"
            else:
                result += str(item)
            
            # Añadir coma si no es el último elemento
            if i < len(arr) - 1:
                result += ","
            
            result += "\n"
        
        # Cerrar el array con indentación adecuada
        result += " " * (current_indent - indent) + "]"
        
        return result