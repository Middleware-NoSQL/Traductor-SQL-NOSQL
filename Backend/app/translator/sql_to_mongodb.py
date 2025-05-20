import logging
from app.parser.sql_parser import SQLParser

# Configurar logging
logger = logging.getLogger(__name__)

class SQLToMongoDBTranslator:
    """
    Traductor de consultas SQL a operaciones MongoDB.
    Convierte los resultados del parser SQL en operaciones MongoDB equivalentes.
    """
    
    def __init__(self, sql_parser=None):
        """
        Inicializa el traductor con un parser SQL opcional.
        
        Args:
            sql_parser (SQLParser, optional): Parser SQL preconfigurado
        """
        self.sql_parser = sql_parser
    
    def translate(self, sql_query=None):
        """
        Traduce una consulta SQL a formato MongoDB.
        
        Args:
            sql_query (str, optional): Consulta SQL a traducir. Si no se proporciona,
                                      se utiliza la consulta del parser proporcionado en la inicialización.
        
        Returns:
            dict: Diccionario con la operación MongoDB equivalente
        """
        # Si se proporciona una nueva consulta, crear un nuevo parser
        if sql_query:
            self.sql_parser = SQLParser(sql_query)
        
        if not self.sql_parser:
            raise ValueError("No se ha proporcionado una consulta SQL ni un parser")
        
        # Determinar el tipo de consulta y llamar al método de traducción adecuado
        query_type = self.sql_parser.get_query_type()
        logger.info(f"Traduciendo consulta de tipo: {query_type}")
        
        if query_type == "SELECT":
            return self.translate_select()
        elif query_type == "INSERT":
            return self.translate_insert()
        elif query_type == "UPDATE":
            return self.translate_update()
        elif query_type == "DELETE":
            return self.translate_delete()
        elif query_type == "CREATE":
            return self.translate_create_table()
        elif query_type == "DROP":
            return self.translate_drop_table()
        else:
            raise ValueError(f"Tipo de consulta no soportado: {query_type}")
    
    def translate_select(self):
        """
        Traduce una consulta SELECT a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección en MongoDB)
        collection = self.sql_parser.get_table_name()
        
        # Obtener los campos a seleccionar
        select_fields = self.sql_parser.get_select_fields()
        
        # Obtener la cláusula WHERE
        where_clause = self.sql_parser.get_where_clause()
        
        # Verificar si hay funciones de agregación
        has_aggregate = False
        if hasattr(self.sql_parser, 'get_functions'):
            functions = self.sql_parser.get_functions()
            has_aggregate = len(functions) > 0
        
        # Verificar si hay GROUP BY
        has_group_by = False
        if hasattr(self.sql_parser, 'get_group_by'):
            group_by = self.sql_parser.get_group_by()
            has_group_by = len(group_by) > 0
        
        # Verificar si hay ORDER BY
        has_order_by = False
        if hasattr(self.sql_parser, 'get_order_by'):
            order_by = self.sql_parser.get_order_by()
            has_order_by = len(order_by) > 0
        
        # Verificar si hay LIMIT
        has_limit = False
        if hasattr(self.sql_parser, 'get_limit'):
            limit = self.sql_parser.get_limit()
            has_limit = limit is not None
        
        # Usar aggregate para consultas complejas, find para consultas simples
        if has_aggregate or has_group_by:
            return self._translate_select_aggregate()
        else:
            return self._translate_select_find()
    
    
    def _translate_select_find(self):
        """
        Traduce una consulta SELECT simple a una operación find() de MongoDB.
        
        Returns:
            dict: Diccionario con la operación find de MongoDB
        """
        result = {
            "operation": "find",
            "query": {}
        }
        
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        if collection:
            result["collection"] = collection
        
        # Obtener cláusula WHERE
        where_clause = self.sql_parser.get_where_clause()
        if where_clause:
            result["query"] = where_clause
        
        # Obtener campos a seleccionar (proyección)
        select_fields = self.sql_parser.get_select_fields()
        
        # Asegurarnos de que select_fields sea una lista
        if isinstance(select_fields, list):
            # Verificar si hay un campo con valor "*"
            if not any(isinstance(field, dict) and field.get("field") == "*" for field in select_fields):
                projection = {}
                for field_info in select_fields:
                    if isinstance(field_info, dict) and "field" in field_info:
                        field = field_info["field"]
                        # Solo incluir campos simples, no funciones
                        if not any(func + "(" in str(field).lower() for func in ["count", "sum", "avg", "min", "max"]):
                            projection[field] = 1
                
                if projection:
                    result["projection"] = projection
        
        # Obtener ORDER BY
        if hasattr(self.sql_parser, 'get_order_by'):
            order_by = self.sql_parser.get_order_by()
            if order_by:
                sort = {}
                for order_info in order_by:
                    field = order_info.get("field")
                    direction = -1 if order_info.get("order") == "DESC" else 1
                    sort[field] = direction
                
                if sort:
                    result["sort"] = sort
        
        # Obtener LIMIT
        if hasattr(self.sql_parser, 'get_limit'):
            limit = self.sql_parser.get_limit()
            if limit is not None:
                logger.debug(f"Traduciendo LIMIT {limit} a MongoDB")
                result["limit"] = limit
                
        logger.debug(f"Consulta MongoDB generada: {result}")
        return result


    def _translate_select_aggregate(self):
        """
        Traduce una consulta SELECT compleja a una operación aggregate() de MongoDB.
        
        Returns:
            dict: Diccionario con la operación aggregate de MongoDB
        """
        pipeline = []
        
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        # 1. Etapa $match inicial (WHERE)
        where_clause = self.sql_parser.get_where_clause()
        if where_clause:
            pipeline.append({
                "$match": where_clause
            })
        
        # 2. Etapa $group (GROUP BY y funciones de agregación)
        if hasattr(self.sql_parser, 'get_group_by') and hasattr(self.sql_parser, 'get_functions'):
            group_by = self.sql_parser.get_group_by()
            functions = self.sql_parser.get_functions()
            
            if group_by or functions:
                group_stage = {"$group": {"_id": {}}}
                
                # Configurar _id para GROUP BY
                if group_by:
                    for field in group_by:
                        group_stage["$group"]["_id"][field] = "$" + field
                else:
                    # Si solo hay funciones sin GROUP BY, usar null como _id
                    group_stage["$group"]["_id"] = None
                
                # Configurar acumuladores para funciones de agregación
                for func in functions:
                    function_type = func.get("function").lower()
                    field = func.get("field")
                    alias = func.get("alias")
                    
                    if function_type == "count" and field == "*":
                        # COUNT(*) se traduce a $sum: 1
                        group_stage["$group"][alias] = {"$sum": 1}
                    elif function_type in ["sum", "avg", "min", "max"]:
                        # Otras funciones tienen equivalentes directos
                        mongo_func = "$" + function_type
                        group_stage["$group"][alias] = {mongo_func: "$" + field}
                
                pipeline.append(group_stage)
                
                # Añadir $project para reorganizar campos
                project_stage = {"$project": {}}
                
                # Proyectar campos de GROUP BY
                if group_by:
                    for field in group_by:
                        project_stage["$project"][field] = "$_id." + field
                
                # Proyectar resultados de funciones
                for func in functions:
                    alias = func.get("alias")
                    project_stage["$project"][alias] = 1
                
                # Ocultar el campo _id
                project_stage["$project"]["_id"] = 0
                
                pipeline.append(project_stage)
        
        # 3. Etapa $sort para ORDER BY
        if hasattr(self.sql_parser, 'get_order_by'):
            order_by = self.sql_parser.get_order_by()
            if order_by:
                sort_stage = {"$sort": {}}
                
                for order_info in order_by:
                    field = order_info.get("field")
                    direction = -1 if order_info.get("order") == "DESC" else 1
                    sort_stage["$sort"][field] = direction
                
                pipeline.append(sort_stage)
        
        # 4. Etapa $limit para LIMIT
        if hasattr(self.sql_parser, 'get_limit'):
            limit = self.sql_parser.get_limit()
            if limit is not None:
                pipeline.append({
                    "$limit": limit
                })
        
        return {
            "operation": "aggregate",
            "collection": collection,
            "pipeline": pipeline
        }
    

    def translate_insert(self):
        """
        Traduce una consulta INSERT a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        # Obtener los valores a insertar
        insert_values = self.sql_parser.get_insert_values()
        
        if not insert_values:
            raise ValueError("No se pudieron extraer valores para insertar")
        
        # Usamos "values" para los valores a insertar
        document = insert_values.get("values", {})
        
        return {
            "operation": "insert",
            "collection": collection,
            "document": document
        }

    
    def translate_update(self):
        """
        Traduce una consulta UPDATE a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        # Obtener valores a actualizar
        update_values = self.sql_parser.get_update_values()
        
        # Obtener condición WHERE
        where_clause = self.sql_parser.get_where_clause()
        
        if not update_values:
            raise ValueError("No se pudieron extraer valores para actualizar")
        
        return {
            "operation": "update",
            "collection": collection,
            "query": {
                "query": where_clause or {},
                "update": {"$set": update_values["values"]}
            }
        }

    
    def translate_delete(self):
        """
        Traduce una consulta DELETE a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        # Obtener condición WHERE
        where_clause = self.sql_parser.get_where_clause()
        
        return {
            "operation": "delete",
            "collection": collection,
            "query": where_clause or {}
        }
    
    def translate_create_table(self):
        """
        Traduce una consulta CREATE TABLE a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        if not collection:
            raise ValueError("No se pudo determinar el nombre de la colección")
        
        # MongoDB crea colecciones automáticamente, pero podemos crear explícitamente
        return {
            "operation": "create_collection",
            "collection": collection,
            "options": {}  # Opciones como validación, etc.
        }
    
    def translate_drop_table(self):
        """
        Traduce una consulta DROP TABLE a operaciones de MongoDB.
        
        Returns:
            dict: Diccionario con la operación MongoDB
        """
        # Obtener el nombre de la tabla (colección)
        collection = self.sql_parser.get_table_name()
        
        if not collection:
            raise ValueError("No se pudo determinar el nombre de la colección")
        
        return {
            "operation": "drop_collection",
            "collection": collection
        }