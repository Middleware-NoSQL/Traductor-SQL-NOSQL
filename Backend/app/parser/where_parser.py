import re
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class WhereParser:
    """
    Parser especializado para cláusulas WHERE de SQL.
    Analiza condiciones WHERE y las convierte a formato MongoDB.
    """
    
    def parse(self, query):
        """
        Analiza la cláusula WHERE de una consulta SQL.
        
        Args:
            query (str): Consulta SQL completa
            
        Returns:
            dict: Diccionario con las condiciones en formato MongoDB
        """
        logger.info(f"Analizando cláusula WHERE de consulta: {query}")
        
        # Extraer la parte WHERE
        where_clause = self.extract_where_clause(query)
        
        if not where_clause:
            return {}
        
        # Analizar las condiciones
        conditions = {}
        self._parse_conditions(where_clause, conditions)
        
        logger.info(f"Condiciones WHERE traducidas: {conditions}")
        return conditions
    
    def extract_where_clause(self, query):
        """
        Extrae la cláusula WHERE de una consulta SQL.
        
        Args:
            query (str): Consulta SQL completa
            
        Returns:
            str: Cláusula WHERE o None si no existe
        """
        # Normalizar la consulta
        query = " " + query.strip() + " "
        
        # Expresión regular para extraer la cláusula WHERE
        pattern = r'\sWHERE\s+(.*?)(?:\sGROUP BY|\sHAVING|\sORDER BY|\sLIMIT|\sOFFSET|\s;|\sUNION|\sINTERSECT|\sEXCEPT|\s$)'
        match = re.search(pattern, query, re.IGNORECASE | re.DOTALL)
        
        if match:
            where_clause = match.group(1).strip()
            logger.info(f"Cláusula WHERE extraída: {where_clause}")
            return where_clause
        
        logger.info("No se encontró cláusula WHERE en la consulta")
        return None
    
    def _parse_conditions(self, conditions_str, result):
        """
        Analiza las condiciones de una cláusula WHERE.
        
        Args:
            conditions_str (str): String con las condiciones
            result (dict): Diccionario donde se almacenarán las condiciones
        """
        # Normalizar la condición
        conditions_str = conditions_str.strip()
        
        # Verificar si hay operadores lógicos a nivel superior
        if self._has_top_level_operator(conditions_str, "OR"):
            # Manejar condiciones OR
            parts = self._split_by_top_level_operator(conditions_str, "OR")
            or_conditions = []
            
            for part in parts:
                part_dict = {}
                self._parse_conditions(part.strip(), part_dict)
                if part_dict:
                    or_conditions.append(part_dict)
            
            if or_conditions:
                result["$or"] = or_conditions
            return
            
        if self._has_top_level_operator(conditions_str, "AND"):
            # Manejar condiciones AND
            parts = self._split_by_top_level_operator(conditions_str, "AND")
            
            for part in parts:
                sub_condition = {}
                self._parse_conditions(part.strip(), sub_condition)
                # Mezclar condiciones AND en el resultado principal
                result.update(sub_condition)
            return
        
        # Si llegamos aquí, es una condición simple
        self._parse_simple_condition(conditions_str, result)
    
    def _parse_simple_condition(self, condition_str, result):
        """
        Analiza una condición simple (sin AND/OR) de una cláusula WHERE.
        
        Args:
            condition_str (str): String con la condición simple
            result (dict): Diccionario donde se almacenará la condición
        """
        # Operadores de comparación estándar
        operators = {
            ">=": "$gte",
            "<=": "$lte",
            "<>": "$ne",
            "!=": "$ne",
            "=": "$eq",
            ">": "$gt",
            "<": "$lt"
        }
        
        # Manejar operadores especiales
        # BETWEEN
        between_match = re.search(r'([\w.]+)\s+BETWEEN\s+(.*?)\s+AND\s+(.*?)(?:\s|$)', condition_str, re.IGNORECASE)
        if between_match:
            field = between_match.group(1).strip()
            min_val = self._parse_value(between_match.group(2).strip())
            max_val = self._parse_value(between_match.group(3).strip())
            result[field] = {"$gte": min_val, "$lte": max_val}
            return
        
        # IN
        in_match = re.search(r'([\w.]+)\s+IN\s+\((.*?)\)', condition_str, re.IGNORECASE)
        if in_match:
            field = in_match.group(1).strip()
            values_str = in_match.group(2).strip()
            values = [self._parse_value(v.strip()) for v in self._split_values(values_str)]
            result[field] = {"$in": values}
            return
        
        # NOT IN - Corregido para usar $nin
        not_in_match = re.search(r'([\w.]+)\s+NOT\s+IN\s+\((.*?)\)', condition_str, re.IGNORECASE)
        if not_in_match:
            field = not_in_match.group(1).strip()
            values_str = not_in_match.group(2).strip()
            values = [self._parse_value(v.strip()) for v in self._split_values(values_str)]
            result[field] = {"$nin": values}
            return
        
        # LIKE
        like_match = re.search(r'([\w.]+)\s+LIKE\s+(.*?)(?:\s|$)', condition_str, re.IGNORECASE)
        if like_match:
            field = like_match.group(1).strip()
            pattern = like_match.group(2).strip()
            if (pattern.startswith("'") and pattern.endswith("'")) or (pattern.startswith('"') and pattern.endswith('"')):
                pattern = pattern[1:-1]  # Quitar comillas
            
            # Convertir patrón SQL a regex MongoDB
            mongo_pattern = pattern.replace("%", ".*").replace("_", ".")
            result[field] = {"$regex": mongo_pattern, "$options": "i"}
            return
        
        # IS NULL
        is_null_match = re.search(r'([\w.]+)\s+IS\s+NULL', condition_str, re.IGNORECASE)
        if is_null_match:
            field = is_null_match.group(1).strip()
            result[field] = {"$exists": False}
            return
        
        # IS NOT NULL
        is_not_null_match = re.search(r'([\w.]+)\s+IS\s+NOT\s+NULL', condition_str, re.IGNORECASE)
        if is_not_null_match:
            field = is_not_null_match.group(1).strip()
            result[field] = {"$exists": True}
            return
        
        # Operadores de comparación estándar
        for op in sorted(operators.keys(), key=len, reverse=True):
            if op in condition_str:
                parts = condition_str.split(op, 1)
                if len(parts) == 2:
                    field = parts[0].strip()
                    value = self._parse_value(parts[1].strip())
                    
                    # Si el operador es '=', podemos usar el valor directamente en MongoDB
                    if op == "=":
                        result[field] = value
                    else:
                        result[field] = {operators[op]: value}
                    return
        
        logger.warning(f"No se pudo analizar la condición: {condition_str}")
    
    def _has_top_level_operator(self, text, operator):
        """
        Verifica si hay un operador específico a nivel superior (fuera de paréntesis).
        
        Args:
            text (str): Texto a analizar
            operator (str): Operador a buscar (AND/OR)
            
        Returns:
            bool: True si hay operador a nivel superior, False en caso contrario
        """
        pattern = r'\s' + operator + r'\s'
        level = 0
        
        for i in range(len(text) - len(operator)):
            if text[i] == '(':
                level += 1
            elif text[i] == ')':
                level -= 1
            elif level == 0 and re.match(pattern, text[i:i+len(operator)+2], re.IGNORECASE):
                return True
        
        return False
    
    def _split_by_top_level_operator(self, text, operator):
        """
        Divide el texto por un operador específico a nivel superior.
        
        Args:
            text (str): Texto a dividir
            operator (str): Operador para dividir (AND/OR)
            
        Returns:
            list: Lista de partes divididas
        """
        result = []
        current = ""
        level = 0
        i = 0
        
        op_pattern = r'\s' + operator + r'\s'
        text = " " + text + " "  # Añadir espacios para facilitar la coincidencia
        
        while i < len(text):
            if text[i] == '(':
                level += 1
                current += text[i]
            elif text[i] == ')':
                level -= 1
                current += text[i]
            elif level == 0 and i <= len(text) - len(operator) - 2:
                # Verificar si esta parte coincide con el operador (con espacios)
                part = text[i:i+len(operator)+2]
                if re.match(op_pattern, part, re.IGNORECASE):
                    # Encontramos el operador, guardamos la parte actual
                    if current.strip():
                        result.append(current.strip())
                    current = ""
                    # Saltar el operador
                    i += len(operator)
                else:
                    current += text[i]
            else:
                current += text[i]
            i += 1
        
        # Añadir la última parte si no está vacía
        if current.strip():
            result.append(current.strip())
        
        return result
    
    def _split_values(self, values_str):
        """
        Divide una lista de valores separados por comas, respetando comillas.
        
        Args:
            values_str (str): String con valores separados por comas
            
        Returns:
            list: Lista de valores individuales
        """
        if not values_str:
            return []
            
        values = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in values_str + ',':  # Añadir coma al final para capturar el último valor
            if char in ["'", '"'] and (not in_quotes or char == quote_char):
                in_quotes = not in_quotes
                current += char
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ""
            else:
                current += char
        
        return values
    
    def _parse_value(self, value_str):
        """
        Parsea un valor desde un string a su tipo adecuado (int, float, bool, None, str).
        
        Args:
            value_str (str): Valor a convertir
            
        Returns:
            El valor convertido al tipo apropiado
        """
        if value_str is None:
            return None
            
        # Limpiar espacios
        value_str = value_str.strip()
        
        # Si está entre comillas, es una cadena
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]
        
        # Si es NULL, devolver None
        if value_str.upper() == "NULL":
            return None
        
        # Si es TRUE o FALSE, devolver booleano
        if value_str.upper() == "TRUE":
            return True
        if value_str.upper() == "FALSE":
            return False
        
        # Si tiene punto decimal, intentar convertir a float
        if "." in value_str:
            try:
                return float(value_str)
            except ValueError:
                pass
        
        # Intentar convertir a entero
        try:
            return int(value_str)
        except ValueError:
            pass
        
        # Si no coincide con ningún tipo, devolver como string
        return value_str