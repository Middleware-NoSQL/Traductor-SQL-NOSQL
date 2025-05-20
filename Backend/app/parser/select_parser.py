import re
import logging
from .base_parser import BaseParser

# Configurar logging
logger = logging.getLogger(__name__)

class SelectParser(BaseParser):
    """
    Parser especializado para consultas SELECT de SQL.
    Analiza y extrae los campos y componentes de una consulta SELECT.
    """
    
    def parse(self, query):
        """
        Analiza una consulta SELECT y extrae sus componentes.
        
        Args:
            query (str): Consulta SELECT a analizar
            
        Returns:
            dict: Diccionario con información de los campos SELECT
        """
        logger.info(f"Analizando consulta SELECT: {query}")
        
        # Extraer los campos a seleccionar
        fields = self.get_select_fields(query)
        
        # Extraer el nombre de la tabla
        table = self.get_table_name(query)
        
        return {
            "operation": "SELECT",
            "fields": fields,
            "table": table
        }
    
    def get_select_fields(self, query):
        """
        Extrae los campos a seleccionar de una consulta SELECT.
        
        Args:
            query (str): Consulta SELECT a analizar
            
        Returns:
            list: Lista de diccionarios con campos y alias
        """
        # Normalizar la consulta
        query = query.strip()
        
        # Obtener la parte entre SELECT y FROM
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, query, re.IGNORECASE | re.DOTALL)
        
        if not select_match:
            logger.warning("No se pudo extraer campos SELECT")
            return [{"field": "*"}]  # Asumir SELECT * si no se puede analizar
        
        fields_str = select_match.group(1).strip()
        
        # Si es SELECT *, devolver un indicador especial
        if fields_str == "*":
            return [{"field": "*"}]
        
        # Dividir los campos por comas, respetando funciones y paréntesis
        fields = self._split_select_fields(fields_str)
        select_fields = []
        
        for field in fields:
            field = field.strip()
            
            # Detectar alias (campo AS alias o campo alias)
            alias_match = re.search(r'(.*?)\s+AS\s+([\w]+)$', field, re.IGNORECASE)
            if not alias_match:
                # Intentar con formato sin AS (campo alias)
                alias_match = re.search(r'(.*?)\s+([\w]+)$', field)
            
            if alias_match:
                field_name = alias_match.group(1).strip()
                alias = alias_match.group(2).strip()
                select_fields.append({"field": field_name, "alias": alias})
            else:
                select_fields.append({"field": field})
        
        logger.info(f"Campos SELECT extraídos: {select_fields}")
        return select_fields
    
    def get_table_name(self, query):
        """
        Extrae el nombre de la tabla de una consulta SELECT.
        
        Args:
            query (str): Consulta SELECT a analizar
            
        Returns:
            str: Nombre de la tabla
        """
        # Normalizar la consulta
        query = query.strip()
        
        # Extraer la parte después de FROM y antes de la siguiente cláusula
        from_pattern = r'FROM\s+([^\s,;()]+)(?:\s+(?:WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|JOIN)|\s*$)'
        from_match = re.search(from_pattern, query, re.IGNORECASE)
        
        if from_match:
            table_name = from_match.group(1).strip('`[]"\'')
            logger.info(f"Tabla extraída: {table_name}")
            return table_name.lower()
        
        # Si el patrón anterior falla, intentar un patrón más simple
        simple_pattern = r'FROM\s+([^\s,;()]+)'
        simple_match = re.search(simple_pattern, query, re.IGNORECASE)
        
        if simple_match:
            table_name = simple_match.group(1).strip('`[]"\'')
            logger.info(f"Tabla extraída (patrón simple): {table_name}")
            return table_name.lower()
        
        logger.warning("No se pudo extraer tabla de SELECT")
        return None
    
    def _split_select_fields(self, fields_str):
        """
        Divide los campos de una cláusula SELECT, respetando funciones y paréntesis.
        
        Args:
            fields_str (str): Cadena con los campos a dividir
            
        Returns:
            list: Lista de campos individuales
        """
        fields = []
        current = ""
        in_quotes = False
        quote_char = None
        level = 0
        
        for char in fields_str + ',':  # Añadir coma al final para capturar el último campo
            if char in ["'", '"'] and (not in_quotes or char == quote_char):
                in_quotes = not in_quotes
                if in_quotes:
                    quote_char = char
                else:
                    quote_char = None
                current += char
            elif char == '(' and not in_quotes:
                level += 1
                current += char
            elif char == ')' and not in_quotes:
                level -= 1
                current += char
            elif char == ',' and level == 0 and not in_quotes:
                fields.append(current.strip())
                current = ""
            else:
                current += char
        
        return fields
    
    def has_aggregate_functions(self, fields):
        """
        Verifica si hay funciones de agregación en los campos seleccionados.
        
        Args:
            fields (list): Lista de diccionarios con campos
            
        Returns:
            bool: True si hay funciones de agregación, False en caso contrario
        """
        agg_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX"]
        
        for field_info in fields:
            field = field_info.get("field", "").upper()
            for func in agg_functions:
                if f"{func}(" in field:
                    return True
        
        return False
    
    def extract_functions(self, fields):
        """
        Extrae información de las funciones de agregación en los campos.
        
        Args:
            fields (list): Lista de diccionarios con campos
            
        Returns:
            list: Lista de diccionarios con información de funciones
        """
        functions = []
        agg_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX"]
        
        for field_info in fields:
            field = field_info.get("field", "")
            alias = field_info.get("alias", "")
            
            for func in agg_functions:
                func_pattern = fr'{func}\s*\((.*?)\)'
                match = re.search(func_pattern, field, re.IGNORECASE)
                
                if match:
                    inner_field = match.group(1).strip()
                    # Si no hay alias, generar uno
                    if not alias:
                        alias = f"{func.lower()}_{inner_field.lower()}"
                        if inner_field == "*":
                            alias = f"{func.lower()}_all"
                    
                    functions.append({
                        "function": func.lower(),
                        "field": inner_field,
                        "alias": alias
                    })
        
        return functions