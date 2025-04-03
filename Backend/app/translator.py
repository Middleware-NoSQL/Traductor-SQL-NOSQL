class SQLToMongoDBTranslator:
    def __init__(self, sql_parser):
        self.sql_parser = sql_parser

    def translate_select(self):
        """
        Traduce una consulta SELECT a MongoDB.
        :return: Consulta en formato MongoDB.
        """
        result = {
            "filter": {},      # Equivalente a WHERE
            "projection": {},  # Campos a devolver
            "sort": None,      # ORDER BY
            "limit": None,     # LIMIT
            "skip": None,      # OFFSET
            "aggregate": None  # Para GROUP BY, HAVING, funciones de agregación, JOIN
        }
        
        # Obtener la cláusula WHERE
        where_clause = self.sql_parser.get_where_clause()
        if where_clause:
            result["filter"] = where_clause
        
        # Obtener campos a seleccionar
        select_fields = self.sql_parser.get_select_fields()
        if select_fields and select_fields[0] != "*":
            projection = {}
            for field_info in select_fields:
                field = field_info.get("field")
                # Si no es una función de agregación (las manejaremos por separado)
                if not any(func + "(" in field.upper() for func in ["COUNT", "SUM", "AVG", "MIN", "MAX"]):
                    projection[field.lower()] = 1
            
            if projection:
                result["projection"] = projection
        
        # Obtener ORDER BY
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
        limit = self.sql_parser.get_limit()
        if limit is not None:
            result["limit"] = limit
        
        # Verificar si necesitamos usar aggregation pipeline
        group_by = self.sql_parser.get_group_by()
        having = self.sql_parser.get_having()
        functions = self.sql_parser.get_functions()
        joins = self.sql_parser.get_joins()
        
        if group_by or having or functions or joins:
            result["aggregate"] = self._build_aggregation_pipeline()
        
        return result

    def _build_aggregation_pipeline(self):
        """
        Construye un aggregation pipeline de MongoDB para consultas complejas.
        :return: Lista de etapas del pipeline.
        """
        pipeline = []
        
        # Añadir etapa $match para filtrar (WHERE)
        where_clause = self.sql_parser.get_where_clause()
        if where_clause:
            pipeline.append({"$match": where_clause})
        
        # Procesar JOINs
        joins = self.sql_parser.get_joins()
        for join in joins:
            join_type = join.get("type").upper()
            join_table = join.get("table")
            join_condition = join.get("condition")
            
            # Dividir la condición de join (tabla1.campo1 = tabla2.campo2)
            if "=" in join_condition:
                left_side, right_side = join_condition.split("=")
                left_side = left_side.strip()
                right_side = right_side.strip()
                
                # Extraer los campos de cada lado
                if "." in left_side and "." in right_side:
                    left_table, left_field = left_side.split(".")
                    right_table, right_field = right_side.split(".")
                    
                    # Determinar si el campo local está a la izquierda o derecha
                    local_field = left_field.lower() if left_table.lower() != join_table.lower() else right_field.lower()
                    foreign_field = right_field.lower() if left_table.lower() != join_table.lower() else left_field.lower()
                    
                    # Construir la etapa $lookup
                    lookup_stage = {
                        "$lookup": {
                            "from": join_table,
                            "localField": local_field,
                            "foreignField": foreign_field,
                            "as": join_table + "_joined"
                        }
                    }
                    pipeline.append(lookup_stage)
                    
                    # Para LEFT JOIN, no necesitamos filtrar los documentos sin coincidencias
                    # Para INNER JOIN, necesitamos filtrar los que no tienen coincidencias
                    if join_type == "INNER JOIN" or join_type == "JOIN":
                        pipeline.append({
                            "$match": {
                                join_table + "_joined": {"$ne": []}
                            }
                        })
                    
                    # Descomponer el array para tener un documento por cada coincidencia
                    pipeline.append({
                        "$unwind": {
                            "path": "$" + join_table + "_joined",
                            "preserveNullAndEmptyArrays": join_type == "LEFT JOIN"
                        }
                    })
        
        # Procesar GROUP BY y funciones de agregación
        group_by = self.sql_parser.get_group_by()
        functions = self.sql_parser.get_functions()
        
        if group_by or functions:
            group_stage = {"$group": {"_id": {}}}
            
            # Configurar campos de agrupación
            if group_by:
                for field in group_by:
                    group_stage["$group"]["_id"][field] = "$" + field
            else:
                # Si hay funciones de agregación sin GROUP BY, usamos NULL como _id
                group_stage["$group"]["_id"] = None
            
            # Añadir funciones de agregación
            for func in functions:
                function_type = func.get("function").lower()
                field = func.get("field")
                alias = func.get("alias")
                
                if function_type == "count" and field == "*":
                    group_stage["$group"][alias] = {"$sum": 1}
                elif function_type in ["sum", "avg", "min", "max"]:
                    mongo_func = "$" + function_type
                    group_stage["$group"][alias] = {mongo_func: "$" + field}
            
            pipeline.append(group_stage)
            
            # Si hay GROUP BY, proyectar los campos para que tengan nombres más amigables
            if group_by:
                project_stage = {"$project": {}}
                
                # Proyectar campos de agrupación
                for field in group_by:
                    project_stage["$project"][field] = "$_id." + field
                
                # Proyectar resultados de funciones
                for func in functions:
                    alias = func.get("alias")
                    project_stage["$project"][alias] = 1
                
                # No necesitamos _id en el resultado final
                project_stage["$project"]["_id"] = 0
                
                pipeline.append(project_stage)
        
        # Procesar HAVING (similar a WHERE pero después de GROUP BY)
        having = self.sql_parser.get_having()
        if having:
            # Convertir referencias de funciones a sus alias correspondientes
            modified_having = {}
            functions = self.sql_parser.get_functions()
            
            for key, value in having.items():
                # Si la clave es una función como "count(*)", buscar su alias
                key_lower = key.lower()
                if key_lower == "count(*)":
                    # Buscar el alias correspondiente en las funciones
                    for func in functions:
                        if func.get("function") == "count" and func.get("field") == "*":
                            alias = func.get("alias")
                            if alias:
                                print(f"Traduciendo referencia de HAVING: {key} -> {alias}")
                                modified_having[alias] = value
                                break
                else:
                    modified_having[key] = value
            
            if modified_having:
                print(f"Cláusula HAVING modificada: {modified_having}")
                pipeline.append({"$match": modified_having})
            else:
                print(f"Usando cláusula HAVING original: {having}")
                pipeline.append({"$match": having})
        
        
        # Procesar ORDER BY
        order_by = self.sql_parser.get_order_by()
        if order_by:
            sort_stage = {"$sort": {}}
            for order_info in order_by:
                field = order_info.get("field")
                direction = -1 if order_info.get("order") == "DESC" else 1
                sort_stage["$sort"][field] = direction
            
            pipeline.append(sort_stage)
        
        # Procesar LIMIT
        limit = self.sql_parser.get_limit()
        if limit is not None:
            pipeline.append({"$limit": limit})
        
        return pipeline

    def translate_insert(self):
        """
        Traduce una consulta INSERT a MongoDB.
        :return: Documento a insertar.
        """
        return self.sql_parser.get_insert_values()

    def translate_update(self):
        """
        Traduce una consulta UPDATE a MongoDB.
        :return: Consulta de actualización en formato MongoDB.
        """
        update_values = self.sql_parser.get_update_values()
        where_clause = self.sql_parser.get_where_clause()
        
        # Verificar que hay valores para actualizar
        if not update_values:
            print("ADVERTENCIA: No se encontraron valores para actualizar")
        
        # Verificar que hay condiciones WHERE
        if not where_clause:
            print("ADVERTENCIA: No se encontró cláusula WHERE, esto actualizará TODOS los documentos")
        
        return {"query": where_clause, "update": {"$set": update_values}}

    def translate_delete(self):
        """
        Traduce una consulta DELETE a MongoDB.
        :return: Consulta de eliminación en formato MongoDB.
        """
        return self.sql_parser.get_where_clause()

    def translate(self):
        """
        Traduce la consulta SQL a MongoDB según su tipo.
        :return: Consulta en formato MongoDB.
        """
        query_type = self.sql_parser.get_query_type()
        print(f"Traduciendo consulta de tipo: {query_type}")
        
        if query_type == "SELECT":
            select_result = self.translate_select()
            
            # Si hay un pipeline de agregación, usar el método aggregate
            if select_result.get("aggregate"):
                return {
                    "operation": "aggregate", 
                    "pipeline": select_result["aggregate"]
                }
            else:
                # Consulta find normal
                result = {
                    "operation": "find", 
                    "query": select_result["filter"]
                }
                
                # Añadir proyección si existe
                if select_result["projection"]:
                    result["projection"] = select_result["projection"]
                
                # Añadir ordenamiento si existe
                if select_result["sort"]:
                    result["sort"] = select_result["sort"]
                
                # Añadir límite si existe
                if select_result["limit"] is not None:
                    result["limit"] = select_result["limit"]
                
                return result
                
        elif query_type == "INSERT":
            return {"operation": "insert", "document": self.translate_insert()}
        elif query_type == "UPDATE":
            return {"operation": "update", "query": self.translate_update()}
        elif query_type == "DELETE":
            return {"operation": "delete", "query": self.translate_delete()}
        
        raise ValueError(f"Tipo de consulta no soportado: {query_type}")