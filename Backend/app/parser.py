import sqlparse
from sqlparse.sql import TokenList, Identifier, Token

class SQLParser:
    def __init__(self, sql_query):
        self.sql_query = sql_query
        self.parsed = sqlparse.parse(sql_query)
        print(f"Consulta SQL recibida para analizar: {sql_query}")

    def get_tokens(self):
        """
        Obtiene los tokens de la consulta SQL.
        :return: Lista de tokens.
        """
        if self.parsed:
            return self.parsed[0].tokens
        return []

    def get_query_type(self):
        """
        Determina el tipo de consulta SQL (SELECT, INSERT, UPDATE, DELETE).
        :return: Tipo de consulta.
        """
        if self.parsed:
            return self.parsed[0].get_type()
        return None

    def get_table_name(self):
        """
        Obtiene el nombre de la tabla (colección) de la consulta SQL.
        :return: Nombre de la tabla como cadena (str).
        """
        query_type = self.get_query_type()
        print(f"Tipo de consulta detectado: {query_type}")
        
        # Método directo por análisis de cadena
        sql = self.sql_query.upper()
        table_name = None
        
        if "SELECT" in sql and "FROM" in sql:
            # Extraer usando el método directo para SELECT
            parts = sql.split("FROM")
            if len(parts) > 1:
                # Tomar la parte después de FROM
                after_from = parts[1].strip()
                # El nombre de la tabla termina en el primer espacio o WHERE
                if "WHERE" in after_from:
                    table_part = after_from.split("WHERE")[0]
                else:
                    table_part = after_from.split()[0] if " " in after_from else after_from
                
                table_name = table_part.strip()
                # Normalizar: convertir a minúsculas para consistencia
                table_name = table_name.lower()
                print(f"Nombre de tabla extraído para SELECT (directo): {table_name}")
                return table_name
        
        elif "INSERT INTO" in sql:
            # Método directo para INSERT
            after_into = sql.split("INSERT INTO")[1].strip()
            if "(" in after_into:
                table_name = after_into.split("(")[0].strip()
            else:
                table_name = after_into.split()[0].strip()
            
            # Normalizar: convertir a minúsculas para consistencia
            table_name = table_name.lower()
            print(f"Nombre de tabla extraído para INSERT (directo): {table_name}")
            return table_name
        
        elif "UPDATE" in sql:
            # Método directo para UPDATE
            after_update = sql.split("UPDATE")[1].strip()
            table_name = after_update.split()[0].strip()
            
            # Normalizar: convertir a minúsculas para consistencia
            table_name = table_name.lower()
            print(f"Nombre de tabla extraído para UPDATE (directo): {table_name}")
            return table_name
        
        elif "DELETE FROM" in sql:
            # Método directo para DELETE
            after_delete = sql.split("DELETE FROM")[1].strip()
            table_name = after_delete.split()[0].strip()
            
            # Normalizar: convertir a minúsculas para consistencia
            table_name = table_name.lower()
            print(f"Nombre de tabla extraído para DELETE (directo): {table_name}")
            return table_name
        
        # Si el método directo no funcionó, intentar con tokens
        print("Intentando extraer nombre de tabla usando tokens...")
        
        if query_type == "SELECT":
            # Buscar el token FROM y tomar el siguiente
            for i, token in enumerate(self.get_tokens()):
                print(f"Token {i}: {token} - Tipo: {token.ttype}")
                if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                    print(f"Encontrado token FROM en posición {i}")
                    if i + 1 < len(self.get_tokens()):
                        table_token = self.get_tokens()[i + 1]
                        print(f"Token siguiente ({i+1}): {table_token}")
                        if isinstance(table_token, sqlparse.sql.Identifier):
                            table_name = table_token.get_real_name()
                        else:
                            table_name = str(table_token).strip()
                        
                        # Normalizar: convertir a minúsculas para consistencia
                        table_name = table_name.lower()
                        print(f"Nombre de tabla extraído para SELECT (tokens): {table_name}")
                        return table_name
            
        # Normalizar el nombre final si se encontró
        if table_name:
            table_name = table_name.lower()
        
        return table_name if table_name else None

    def get_where_clause(self):
        """
        Obtiene la cláusula WHERE de una consulta SQL.
        :return: Diccionario con las condiciones.
        """
        where_clause = {}
        
        # Buscar el token WHERE
        for token in self.get_tokens():
            if isinstance(token, sqlparse.sql.Where):
                print(f"Token WHERE encontrado: {token}")
                conditions_str = str(token).replace("WHERE", "", 1).strip()
                print(f"Condiciones encontradas: {conditions_str}")
                
                # Analizar condiciones
                self._parse_conditions(conditions_str, where_clause)
                break
        
        # Si no se encontró el token WHERE, buscar manualmente en la cadena SQL
        if not where_clause and "WHERE" in self.sql_query.upper():
            try:
                conditions_str = self.sql_query.split("WHERE")[1].strip()
                print(f"Condiciones extraídas manualmente: {conditions_str}")
                self._parse_conditions(conditions_str, where_clause)
            except Exception as e:
                print(f"Error al extraer condiciones WHERE manualmente: {e}")
        
        print(f"Cláusula WHERE generada: {where_clause}")
        return where_clause
    
    def _parse_conditions(self, conditions_str, where_clause):
        """
        Parsea las condiciones de la cláusula WHERE.
        """
        try:
            # Detectar operadores BETWEEN para manejarlos como un caso especial
            # ya que contienen la palabra "AND" que no debe dividirse
            between_pattern = r'(\w+)\s+BETWEEN\s+([^\s]+)\s+AND\s+([^\s]+)'
            import re
            between_matches = re.findall(between_pattern, conditions_str, re.IGNORECASE)
            
            if between_matches:
                print(f"Detectada expresión BETWEEN: {between_matches[0]}")
                # Si toda la condición es un BETWEEN simple
                if len(between_matches) == 1 and conditions_str.upper().count('AND') == 1:
                    self._parse_single_condition(conditions_str, where_clause)
                    return
            
            # Manejar condiciones complejas con paréntesis
            if "(" in conditions_str and ")" in conditions_str:
                # Intentamos manejar grupos de condiciones
                # Esto es una simplificación y no maneja anidamiento profundo
                if " OR " in conditions_str:
                    or_parts = []
                    # Dividir por OR respetando paréntesis
                    parts = self._split_preserving_parentheses(conditions_str, " OR ")
                    
                    for part in parts:
                        part_condition = {}
                        # Si es un grupo entre paréntesis, quitarlos
                        if part.startswith("(") and part.endswith(")"):
                            part = part[1:-1].strip()
                        
                        # Analizar esta parte como una condición independiente
                        self._parse_conditions(part, part_condition)
                        if part_condition:
                            or_parts.append(part_condition)
                    
                    if or_parts:
                        # Añadir como condición $or
                        where_clause["$or"] = or_parts
                    return
                
                elif " AND " in conditions_str:
                    # Dividir por AND respetando paréntesis y BETWEEN
                    parts = self._split_preserving_parentheses(conditions_str, " AND ")
                    
                    # Verificar si alguna parte contiene BETWEEN
                    between_parts = []
                    normal_parts = []
                    
                    for part in parts:
                        if " BETWEEN " in part.upper():
                            between_parts.append(part)
                        else:
                            normal_parts.append(part)
                    
                    # Procesar partes BETWEEN manteniendo el "AND" original
                    for between_part in between_parts:
                        self._parse_single_condition(between_part, where_clause)
                    
                    # Procesar partes normales
                    for part in normal_parts:
                        # Si es un grupo entre paréntesis, quitarlos
                        if part.startswith("(") and part.endswith(")"):
                            part = part[1:-1].strip()
                        
                        # Analizar esta parte como una condición independiente
                        self._parse_conditions(part, where_clause)
                    
                    return
            
            # Comprobar si hay condiciones OR sencillas
            if " OR " in conditions_str:
                or_conditions = [cond.strip() for cond in conditions_str.split(" OR ")]
                or_parts = []
                
                for condition in or_conditions:
                    condition_dict = {}
                    self._parse_single_condition(condition, condition_dict)
                    if condition_dict:
                        or_parts.append(condition_dict)
                
                if or_parts:
                    where_clause["$or"] = or_parts
                return
            
            # Comprobar si hay un BETWEEN en la condición
            if " BETWEEN " in conditions_str and " AND " in conditions_str:
                self._parse_single_condition(conditions_str, where_clause)
                return
                
            # Comprobar si hay condiciones AND sencillas
            # (excluyendo el AND que podría ser parte de BETWEEN)
            if " AND " in conditions_str and " BETWEEN " not in conditions_str:
                and_conditions = [cond.strip() for cond in conditions_str.split(" AND ")]
                
                for condition in and_conditions:
                    self._parse_single_condition(condition, where_clause)
                return
            
            # Si llegamos aquí, es una condición simple
            self._parse_single_condition(conditions_str, where_clause)
        
        except Exception as e:
            print(f"Error al parsear condiciones: {e}")
            import traceback
            print(traceback.format_exc())

    def _split_preserving_parentheses(self, text, delimiter):
        """
        Divide un texto por un delimitador, pero respeta los paréntesis.
        """
        result = []
        current = ""
        paren_level = 0
        i = 0
        
        while i < len(text):
            # Verificar si estamos en el delimitador
            if (paren_level == 0 and 
                i <= len(text) - len(delimiter) and 
                text[i:i+len(delimiter)] == delimiter):
                
                # Añadir la parte actual al resultado
                if current.strip():
                    result.append(current.strip())
                
                # Avanzar por el delimitador
                i += len(delimiter)
                current = ""
            else:
                # Manejar paréntesis
                if text[i] == '(':
                    paren_level += 1
                elif text[i] == ')':
                    paren_level -= 1
                
                # Añadir el carácter actual
                current += text[i]
                i += 1
        
        # Añadir la última parte
        if current.strip():
            result.append(current.strip())
        
        return result


    # Añadir estos métodos a la clase SQLParser en parser.py

    def get_select_fields(self):
        """
        Obtiene los campos a seleccionar de una consulta SELECT.
        :return: Lista de campos a seleccionar.
        """
        select_fields = []
        
        try:
            sql = self.sql_query.upper()
            if "SELECT" in sql:
                # Extraer la parte entre SELECT y FROM
                parts = sql.split("SELECT")[1].split("FROM")[0].strip()
                
                # Si es SELECT *, devolver un campo especial para indicar todos los campos
                if parts.strip() == "*":
                    return ["*"]
                
                # Dividir por comas para obtener los campos individuales
                fields = [field.strip() for field in parts.split(",")]
                
                # Procesar cada campo para manejar alias, funciones, etc.
                for field in fields:
                    # Manejar alias (campo AS alias)
                    if " AS " in field:
                        field_parts = field.split(" AS ")
                        field_name = field_parts[0].strip()
                        alias = field_parts[1].strip()
                        select_fields.append({"field": field_name, "alias": alias})
                    else:
                        select_fields.append({"field": field})
                
                print(f"Campos a seleccionar: {select_fields}")
            
            return select_fields
        except Exception as e:
            print(f"Error al obtener campos SELECT: {e}")
            import traceback
            print(traceback.format_exc())
            # Corregir para devolver una lista de diccionarios en lugar de solo "*"
            return [{"field": "*"}]


    def get_joins(self):
        """
        Obtiene las cláusulas JOIN de una consulta SQL.
        :return: Lista de joins con sus condiciones.
        """
        joins = []
        
        try:
            sql = self.sql_query.upper()
            join_types = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "JOIN"]
            
            # Buscar todos los tipos de JOIN en la consulta
            for join_type in join_types:
                if join_type in sql:
                    # Dividir la consulta por el tipo de JOIN para encontrar todas las ocurrencias
                    parts = sql.split(join_type)
                    
                    # El primer elemento es la parte antes del primer JOIN, omitirlo
                    for i in range(1, len(parts)):
                        join_part = parts[i].strip()
                        
                        # Encontrar la tabla del JOIN
                        if " ON " in join_part:
                            table_name = join_part.split(" ON ")[0].strip()
                            condition = join_part.split(" ON ")[1].strip()
                            
                            # Limpiar la condición si hay más cláusulas después
                            for clause in ["WHERE", "GROUP BY", "ORDER BY", "HAVING"]:
                                if f" {clause} " in condition:
                                    condition = condition.split(f" {clause} ")[0].strip()
                            
                            joins.append({
                                "type": join_type,
                                "table": table_name.lower(),
                                "condition": condition
                            })
            
            print(f"JOINs encontrados: {joins}")
            return joins
        except Exception as e:
            print(f"Error al obtener JOINs: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_group_by(self):
        """
        Obtiene las cláusulas GROUP BY de una consulta SQL.
        :return: Lista de campos para agrupar.
        """
        group_by = []
        
        try:
            sql = self.sql_query.upper()
            if "GROUP BY" in sql:
                # Extraer la parte después de GROUP BY
                group_part = sql.split("GROUP BY")[1].strip()
                
                # Limpiar si hay más cláusulas después
                for clause in ["HAVING", "ORDER BY"]:
                    if f" {clause} " in group_part:
                        group_part = group_part.split(f" {clause} ")[0].strip()
                
                # Dividir por comas para obtener los campos individuales
                fields = [field.strip().lower() for field in group_part.split(",")]
                group_by.extend(fields)
                
                print(f"Campos GROUP BY: {group_by}")
            
            return group_by
        except Exception as e:
            print(f"Error al obtener GROUP BY: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_having(self):
        """
        Obtiene las cláusulas HAVING de una consulta SQL.
        :return: Diccionario con las condiciones HAVING.
        """
        having_clause = {}
        
        try:
            sql = self.sql_query.upper()
            if "HAVING" in sql:
                # Extraer la parte después de HAVING
                having_part = sql.split("HAVING")[1].strip()
                
                # Limpiar si hay más cláusulas después
                if " ORDER BY " in having_part:
                    having_part = having_part.split(" ORDER BY ")[0].strip()
                
                print(f"Cláusula HAVING encontrada: {having_part}")
                
                # Analizar condiciones similar a WHERE
                # (Puedes reutilizar la lógica de _parse_conditions)
                self._parse_conditions(having_part, having_clause)
            
            return having_clause
        except Exception as e:
            print(f"Error al obtener HAVING: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    def get_order_by(self):
        """
        Obtiene las cláusulas ORDER BY de una consulta SQL.
        :return: Lista de campos para ordenar con su dirección.
        """
        order_by = []
        
        try:
            sql = self.sql_query.upper()
            if "ORDER BY" in sql:
                # Extraer la parte después de ORDER BY
                order_part = sql.split("ORDER BY")[1].strip()
                
                # Limpiar otras cláusulas que puedan seguir a ORDER BY
                for clause in ["LIMIT", "OFFSET"]:
                    if f" {clause} " in order_part:
                        order_part = order_part.split(f" {clause} ")[0].strip()
                    elif order_part.endswith(f" {clause}"):
                        order_part = order_part[:-len(f" {clause}")].strip()
                
                # Dividir por comas para obtener los campos individuales
                fields = [field.strip() for field in order_part.split(",")]
                
                for field in fields:
                    if " DESC" in field:
                        field_name = field.replace(" DESC", "").strip().lower()
                        order_by.append({"field": field_name, "order": "DESC"})
                    elif " ASC" in field:
                        field_name = field.replace(" ASC", "").strip().lower()
                        order_by.append({"field": field_name, "order": "ASC"})
                    else:
                        order_by.append({"field": field.lower(), "order": "ASC"})
                
                print(f"Campos ORDER BY: {order_by}")
            
            return order_by
        except Exception as e:
            print(f"Error al obtener ORDER BY: {e}")
            import traceback
            print(traceback.format_exc())
            return []


    def get_limit(self):
        """
        Obtiene la cláusula LIMIT de una consulta SQL.
        :return: Valor del límite o None si no hay.
        """
        try:
            sql = self.sql_query.upper()
            if "LIMIT" in sql:
                # Extraer la parte después de LIMIT
                limit_part = sql.split("LIMIT")[1].strip()
                
                # Convertir a entero
                limit = int(limit_part.split()[0])
                print(f"LIMIT encontrado: {limit}")
                return limit
            
            return None
        except Exception as e:
            print(f"Error al obtener LIMIT: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def get_functions(self):
        """
        Identifica funciones de agregación (COUNT, SUM, AVG, etc.) en una consulta SELECT.
        :return: Lista con funciones encontradas.
        """
        functions = []
        
        try:
            # Obtener los campos SELECT
            select_fields = self.get_select_fields()
            
            # Funciones comunes de SQL
            sql_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX"]
            
            for field_info in select_fields:
                # Verificar si field_info es diccionario o string
                if isinstance(field_info, dict):
                    field = field_info.get("field", "")
                elif isinstance(field_info, str):
                    # Si es "*", saltar
                    if field_info == "*":
                        continue
                    field = field_info
                else:
                    continue
                
                # Verificar si es una función
                for func in sql_functions:
                    if f"{func}(" in field.upper():
                        # Extraer el campo dentro de la función
                        inner_field = field.upper().split(f"{func}(")[1].split(")")[0].strip()
                        
                        # Manejar COUNT(*) especialmente
                        if func == "COUNT" and inner_field == "*":
                            if isinstance(field_info, dict) and "alias" in field_info:
                                alias = field_info.get("alias")
                            else:
                                alias = f"{func.lower()}_result"
                            
                            functions.append({
                                "function": func.lower(),
                                "field": "*",
                                "alias": alias
                            })
                        else:
                            if isinstance(field_info, dict) and "alias" in field_info:
                                alias = field_info.get("alias")
                            else:
                                alias = f"{func.lower()}_{inner_field.lower()}"
                            
                            functions.append({
                                "function": func.lower(),
                                "field": inner_field.lower(),
                                "alias": alias
                            })
            
            print(f"Funciones de agregación encontradas: {functions}")
            return functions
        except Exception as e:
            print(f"Error al obtener funciones: {e}")
            import traceback
            print(traceback.format_exc())
            return []


    def _parse_complex_conditions(self, conditions_str, where_clause):
        """
        Parsea condiciones WHERE más complejas como IN, BETWEEN, LIKE, EXISTS, etc.
        """
        try:
            # Operadores complejos
            complex_ops = {
                "LIKE": "$regex",
                "IN": "$in",
                "NOT IN": "$nin",
                "BETWEEN": "between",
                "IS NULL": "$exists",
                "IS NOT NULL": "$exists"
            }
            
            # Dividir por AND si está presente
            if " AND " in conditions_str:
                conditions = [cond.strip() for cond in conditions_str.split(" AND ")]
            # Dividir por OR si está presente
            elif " OR " in conditions_str:
                conditions = [cond.strip() for cond in conditions_str.split(" OR ")]
                # Manejar OR de manera especial (con $or)
                or_conditions = []
                for condition in conditions:
                    condition_dict = {}
                    self._parse_single_condition(condition, condition_dict)
                    if condition_dict:
                        or_conditions.append(condition_dict)
                
                if or_conditions:
                    where_clause["$or"] = or_conditions
                    return
            else:
                conditions = [conditions_str.strip()]
            
            for condition in conditions:
                self._parse_single_condition(condition, where_clause)
        
        except Exception as e:
            print(f"Error al parsear condiciones complejas: {e}")
            import traceback
            print(traceback.format_exc())

    def _parse_single_condition(self, condition, where_clause):
        """
        Parsea una condición individual de WHERE.
        """
        try:
            print(f"Analizando condición: {condition}")
            
            # Manejar operadores complejos
            
            # LIKE
            if " LIKE " in condition:
                parts = condition.split(" LIKE ")
                field = parts[0].strip().lower()
                value = parts[1].strip()
                
                # Convertir patrón SQL a regex de MongoDB
                # Reemplazar % por .* y _ por .
                if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]  # Quitar comillas
                
                pattern = value.replace("%", ".*").replace("_", ".")
                where_clause[field] = {"$regex": pattern, "$options": "i"}  # i para case-insensitive
                print(f"Condición LIKE procesada: {field} = {pattern}")
                return
            
            # IN
            elif " IN " in condition:
                parts = condition.split(" IN ")
                field = parts[0].strip().lower()
                value_list = parts[1].strip()
                
                # Extraer valores entre paréntesis
                if value_list.startswith("(") and value_list.endswith(")"):
                    values = [val.strip() for val in value_list[1:-1].split(",")]
                    
                    # Convertir valores si es necesario
                    converted_values = []
                    for val in values:
                        if val.startswith("'") and val.endswith("'") or val.startswith('"') and val.endswith('"'):
                            converted_values.append(val[1:-1])  # String sin comillas
                        else:
                            try:
                                if '.' in val:
                                    converted_values.append(float(val))
                                else:
                                    converted_values.append(int(val))
                            except ValueError:
                                converted_values.append(val)
                    
                    where_clause[field] = {"$in": converted_values}
                    print(f"Condición IN procesada: {field} en {converted_values}")
                return
            
            # NOT IN
            elif " NOT IN " in condition:
                parts = condition.split(" NOT IN ")
                field = parts[0].strip().lower()
                value_list = parts[1].strip()
                
                # Extraer valores entre paréntesis
                if value_list.startswith("(") and value_list.endswith(")"):
                    values = [val.strip() for val in value_list[1:-1].split(",")]
                    
                    # Convertir valores si es necesario
                    converted_values = []
                    for val in values:
                        if val.startswith("'") and val.endswith("'") or val.startswith('"') and val.endswith('"'):
                            converted_values.append(val[1:-1])  # String sin comillas
                        else:
                            try:
                                if '.' in val:
                                    converted_values.append(float(val))
                                else:
                                    converted_values.append(int(val))
                            except ValueError:
                                converted_values.append(val)
                    
                    where_clause[field] = {"$nin": converted_values}
                    print(f"Condición NOT IN procesada: {field} no en {converted_values}")
                return
            
            # BETWEEN
            elif " BETWEEN " in condition and " AND " in condition:
                parts = condition.split(" BETWEEN ")
                field = parts[0].strip().lower()
                
                range_parts = parts[1].split(" AND ")
                min_val = range_parts[0].strip()
                max_val = range_parts[1].strip()
                
                # Convertir valores si es necesario
                if min_val.startswith("'") and min_val.endswith("'") or min_val.startswith('"') and min_val.endswith('"'):
                    min_val = min_val[1:-1]
                else:
                    try:
                        if '.' in min_val:
                            min_val = float(min_val)
                        else:
                            min_val = int(min_val)
                    except ValueError:
                        pass
                
                if max_val.startswith("'") and max_val.endswith("'") or max_val.startswith('"') and max_val.endswith('"'):
                    max_val = max_val[1:-1]
                else:
                    try:
                        if '.' in max_val:
                            max_val = float(max_val)
                        else:
                            max_val = int(max_val)
                    except ValueError:
                        pass
                
                where_clause[field] = {"$gte": min_val, "$lte": max_val}
                print(f"Condición BETWEEN procesada: {field} entre {min_val} y {max_val}")
                return
            
            # IS NULL / IS NOT NULL
            elif " IS NULL" in condition:
                field = condition.replace(" IS NULL", "").strip().lower()
                where_clause[field] = {"$exists": False}
                print(f"Condición IS NULL procesada: {field} no existe")
                return
            
            elif " IS NOT NULL" in condition:
                field = condition.replace(" IS NOT NULL", "").strip().lower()
                where_clause[field] = {"$exists": True}
                print(f"Condición IS NOT NULL procesada: {field} existe")
                return
            
            # EXISTS / NOT EXISTS (simplificado)
            elif "EXISTS" in condition:
                print("Advertencia: Operador EXISTS no soportado completamente en esta versión")
                return
            
            # Manejar operadores de comparación estándar
            replacements = {
                ">=": "$gte",
                "<=": "$lte",
                "<>": "$ne",
                "!=": "$ne",
                "=": "$eq",
                ">": "$gt",
                "<": "$lt"
            }
            
            op_found = False
            for op in sorted(replacements.keys(), key=len, reverse=True):
                if op in condition:
                    parts = condition.split(op)
                    if len(parts) == 2:
                        field = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # Limpiar comillas y convertir valor si es necesario
                        if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]  # Quitar comillas
                        else:
                            # Intentar convertir a número
                            try:
                                if '.' in value:
                                    value = float(value)
                                else:
                                    value = int(value)
                            except ValueError:
                                pass  # Mantener como string si no se puede convertir
                        
                        # Para operadores especiales como >, <, >=, etc.
                        if op in ["=", "=="]:
                            where_clause[field] = value
                        else:
                            # Usar el operador de MongoDB
                            if field not in where_clause:
                                where_clause[field] = {}
                            where_clause[field][replacements[op]] = value
                        
                        op_found = True
                        print(f"Operador estándar procesado: {field} {op} {value}")
                        break
            
            if not op_found:
                print(f"No se encontró operador en la condición: {condition}")
        
        except Exception as e:
            print(f"Error al parsear condición individual: {e}")
            import traceback
            print(traceback.format_exc())

    
# Modificación para el método get_insert_values() en parser.py

    def get_insert_values(self):
        """
        Obtiene los valores a insertar de una consulta INSERT INTO.
        :return: Diccionario con los valores a insertar.
        """
        print("Extrayendo valores de inserción de la consulta INSERT")
        insert_values = {}
        
        try:
            # Importante: usamos upper() solo para detectar palabras clave, pero mantenemos
            # la consulta original para extraer los valores
            sql_upper = self.sql_query.upper()
            sql_original = self.sql_query
            
            if "INSERT INTO" in sql_upper:
                # Extraer la parte después de INSERT INTO
                after_into_index = sql_upper.find("INSERT INTO") + len("INSERT INTO")
                after_into = sql_original[after_into_index:].strip()
                
                # Extraer tabla y columnas
                if "(" in after_into and ")" in after_into:
                    # Formato: INSERT INTO tabla (col1, col2) VALUES (val1, val2)
                    table_part = after_into.split("(")[0].strip()
                    
                    # Extraer columnas
                    columns_part = after_into.split("(")[1].split(")")[0].strip()
                    columns = [col.strip() for col in columns_part.split(",")]
                    
                    # Extraer valores
                    if "VALUES" in sql_upper:
                        values_part_index = sql_original.upper().find("VALUES") + len("VALUES")
                        values_part = sql_original[values_part_index:].strip()
                        
                        if values_part.startswith("(") and ")" in values_part:
                            values_list = values_part.split("(")[1].split(")")[0].strip()
                            values = []
                            
                            # Procesar la lista de valores respetando las comillas
                            in_quote = False
                            quote_char = None
                            current_value = ""
                            
                            for char in values_list:
                                if char in ["'", '"'] and (not in_quote or char == quote_char):
                                    in_quote = not in_quote
                                    if in_quote:
                                        quote_char = char
                                    else:
                                        quote_char = None
                                    current_value += char
                                elif char == "," and not in_quote:
                                    values.append(current_value.strip())
                                    current_value = ""
                                else:
                                    current_value += char
                            
                            # Añadir el último valor
                            if current_value.strip():
                                values.append(current_value.strip())
                            
                            print(f"Columnas encontradas: {columns}")
                            print(f"Valores encontrados: {values}")
                            
                            # Combinar columnas y valores
                            if len(columns) == len(values):
                                for i, column in enumerate(columns):
                                    value = values[i]
                                    
                                    # Procesar el valor
                                    if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                                        # Es una cadena - Preservamos el valor original
                                        insert_values[column] = value[1:-1]
                                    else:
                                        # Intentar convertir a número
                                        try:
                                            if '.' in value:
                                                insert_values[column] = float(value)
                                            else:
                                                insert_values[column] = int(value)
                                        except ValueError:
                                            # Si no se puede convertir, mantener como está
                                            insert_values[column] = value
                            else:
                                print(f"ERROR: El número de columnas ({len(columns)}) no coincide con el número de valores ({len(values)})")
                
                else:
                    # Formato simplificado: INSERT INTO tabla VALUES (val1, val2)
                    print("Formato INSERT INTO sin especificar columnas no soportado completamente")
            
            print(f"Valores de inserción extraídos: {insert_values}")
            return insert_values
        
        except Exception as e:
            print(f"Error al extraer valores de inserción: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    def get_update_values(self):
        """
        Obtiene los valores a actualizar de una consulta UPDATE.
        :return: Diccionario con los valores a actualizar.
        """
        print("Extrayendo valores de actualización de la consulta UPDATE")
        update_values = {}
        
        try:
            sql = self.sql_query.upper()
            
            if "UPDATE" in sql and "SET" in sql:
                # Extraer la parte después de SET
                set_part = sql.split("SET")[1].strip()
                
                # Si hay WHERE, obtener solo la parte antes de WHERE
                if "WHERE" in set_part:
                    set_part = set_part.split("WHERE")[0].strip()
                
                # Dividir por comas para obtener cada asignación por separado
                assignments = []
                in_quote = False
                quote_char = None
                current_assignment = ""
                
                for char in set_part:
                    if char in ["'", '"'] and (not in_quote or char == quote_char):
                        in_quote = not in_quote
                        if in_quote:
                            quote_char = char
                        else:
                            quote_char = None
                        current_assignment += char
                    elif char == "," and not in_quote:
                        assignments.append(current_assignment.strip())
                        current_assignment = ""
                    else:
                        current_assignment += char
                
                # Añadir la última asignación
                if current_assignment.strip():
                    assignments.append(current_assignment.strip())
                
                print(f"Asignaciones encontradas: {assignments}")
                
                # Procesar cada asignación (campo = valor)
                for assignment in assignments:
                    if "=" in assignment:
                        parts = assignment.split("=")
                        field = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # Procesar el valor
                        if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                            # Es una cadena
                            update_values[field] = value[1:-1]
                        else:
                            # Intentar convertir a número
                            try:
                                if '.' in value:
                                    update_values[field] = float(value)
                                else:
                                    update_values[field] = int(value)
                            except ValueError:
                                # Si no se puede convertir, mantener como está
                                update_values[field] = value
                    else:
                        print(f"ADVERTENCIA: No se encontró operador '=' en la asignación: {assignment}")
            
            print(f"Valores de actualización extraídos: {update_values}")
            return update_values
        
        except Exception as e:
            print(f"Error al extraer valores de actualización: {e}")
            import traceback
            print(traceback.format_exc())
            return {}