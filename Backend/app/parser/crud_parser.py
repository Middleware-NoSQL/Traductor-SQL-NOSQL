import re
import logging
from .base_parser import BaseParser

# Configurar logging
logger = logging.getLogger(__name__)

class CRUDParser(BaseParser):
    """
    Parser especializado para operaciones CRUD (Create, Read, Update, Delete).
    Analiza consultas INSERT, UPDATE y DELETE.
    """
    
    def parse(self, query):
        """
        Determina el tipo de operación CRUD y redirige al método específico.
        
        Args:
            query (str): Consulta SQL a analizar
            
        Returns:
            dict: Resultado del análisis
        """
        query = query.strip()
        query_upper = query.upper()
        
        if query_upper.startswith('INSERT'):
            return self.parse_insert(query)
        elif query_upper.startswith('UPDATE'):
            return self.parse_update(query)
        elif query_upper.startswith('DELETE'):
            return self.parse_delete(query)
        else:
            raise ValueError(f"Consulta no soportada por CRUDParser: {query}")
    
    def parse_insert(self, query):
        """
        Analiza una consulta INSERT y extrae los valores a insertar.
        
        Args:
            query (str): Consulta INSERT a analizar
            
        Returns:
            dict: Diccionario con tabla y valores a insertar
        """
        logger.info(f"Analizando consulta INSERT: {query}")
        
        # Normalizar la consulta
        query = query.strip()
        
        # Extraer nombre de tabla
        table_pattern = r'INSERT\s+INTO\s+([^\s(]+)'
        table_match = re.search(table_pattern, query, re.IGNORECASE)
        
        if not table_match:
            logger.error("No se pudo extraer tabla de INSERT")
            return {"error": "No se pudo extraer tabla"}
            
        table_name = table_match.group(1).strip('`[]"\'').lower()
        
        # Extraer columnas y valores
        columns_pattern = r'INSERT\s+INTO\s+[^\s(]+\s*\((.*?)\)\s*VALUES\s*\((.*?)\)'
        columns_match = re.search(columns_pattern, query, re.IGNORECASE | re.DOTALL)
        
        if columns_match:
            # INSERT INTO tabla (col1, col2) VALUES (val1, val2)
            columns_str = columns_match.group(1).strip()
            values_str = columns_match.group(2).strip()
            
            columns = [col.strip() for col in self._split_values(columns_str)]
            values = [self._parse_value(val) for val in self._split_values(values_str)]
            
            if len(columns) != len(values):
                logger.error(f"Número de columnas ({len(columns)}) no coincide con número de valores ({len(values)})")
                return {"error": "Número de columnas no coincide con número de valores"}
                
            # Crear diccionario de valores
            insert_data = dict(zip(columns, values))
            
            return {
                "operation": "INSERT",
                "table": table_name,
                "values": insert_data
            }
        else:
            # Intentar con formato sin columnas: INSERT INTO tabla VALUES (val1, val2)
            simple_pattern = r'INSERT\s+INTO\s+[^\s(]+\s+VALUES\s*\((.*?)\)'
            simple_match = re.search(simple_pattern, query, re.IGNORECASE | re.DOTALL)
            
            if simple_match:
                values_str = simple_match.group(1).strip()
                values = [self._parse_value(val) for val in self._split_values(values_str)]
                
                # Usar nombres genéricos de columnas
                columns = [f"column_{i+1}" for i in range(len(values))]
                insert_data = dict(zip(columns, values))
                
                return {
                    "operation": "INSERT",
                    "table": table_name,
                    "values": insert_data
                }
            
            logger.error("No se pudo extraer valores de INSERT")
            return {"error": "No se pudo extraer valores"}
    
    def parse_update(self, query):
        """
        Analiza una consulta UPDATE y extrae los valores a actualizar.
        
        Args:
            query (str): Consulta UPDATE a analizar
            
        Returns:
            dict: Diccionario con tabla, valores y condición
        """
        logger.info(f"Analizando consulta UPDATE: {query}")
        
        # Normalizar la consulta
        query = query.strip()
        
        # Extraer nombre de tabla
        table_pattern = r'UPDATE\s+([^\s,;()]+)'
        table_match = re.search(table_pattern, query, re.IGNORECASE)
        
        if not table_match:
            logger.error("No se pudo extraer tabla de UPDATE")
            return {"error": "No se pudo extraer tabla"}
            
        table_name = table_match.group(1).strip('`[]"\'').lower()
        
        # Extraer valores a actualizar (SET)
        set_pattern = r'SET\s+(.*?)(?:\sWHERE|\s;|\Z)'
        set_match = re.search(set_pattern, query, re.IGNORECASE | re.DOTALL)
        
        if not set_match:
            logger.error("No se pudo extraer cláusula SET de UPDATE")
            return {"error": "No se pudo extraer valores a actualizar"}
            
        set_str = set_match.group(1).strip()
        
        # Dividir las asignaciones por comas
        assignments = self._split_values(set_str)
        update_values = {}
        
        for assignment in assignments:
            if '=' in assignment:
                field, value_str = [part.strip() for part in assignment.split('=', 1)]
                value = self._parse_value(value_str)
                update_values[field.lower()] = value
        
        # Extraer condición WHERE
        where_pattern = r'WHERE\s+(.*?)(?:\s;|\Z)'
        where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
        
        where_condition = {}
        if where_match:
            # Utilizaríamos WhereParser, pero para evitar dependencias circulares,
            # implementamos una versión simplificada aquí.
            where_str = where_match.group(1).strip()
            
            # Procesamiento básico de condición (para consultas simples)
            if '=' in where_str and 'AND' not in where_str.upper() and 'OR' not in where_str.upper():
                field, value_str = [part.strip() for part in where_str.split('=', 1)]
                value = self._parse_value(value_str)
                where_condition[field.lower()] = value
        
        return {
            "operation": "UPDATE",
            "table": table_name,
            "values": update_values,
            "condition": where_condition
        }
    
    def parse_delete(self, query):
        """
        Analiza una consulta DELETE y extrae la condición.
        
        Args:
            query (str): Consulta DELETE a analizar
            
        Returns:
            dict: Diccionario con tabla y condición
        """
        logger.info(f"Analizando consulta DELETE: {query}")
        
        # Normalizar la consulta
        query = query.strip()
        
        # Extraer nombre de tabla
        table_pattern = r'DELETE\s+FROM\s+([^\s,;()]+)'
        table_match = re.search(table_pattern, query, re.IGNORECASE)
        
        if not table_match:
            logger.error("No se pudo extraer tabla de DELETE")
            return {"error": "No se pudo extraer tabla"}
            
        table_name = table_match.group(1).strip('`[]"\'').lower()
        
        # Extraer condición WHERE
        where_pattern = r'WHERE\s+(.*?)(?:\s;|\Z)'
        where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
        
        where_condition = {}
        if where_match:
            # Utilizaríamos WhereParser, pero para evitar dependencias circulares,
            # implementamos una versión simplificada aquí.
            where_str = where_match.group(1).strip()
            
            # Procesamiento básico de condición (para consultas simples)
            if '=' in where_str and 'AND' not in where_str.upper() and 'OR' not in where_str.upper():
                field, value_str = [part.strip() for part in where_str.split('=', 1)]
                value = self._parse_value(value_str)
                where_condition[field.lower()] = value
        
        return {
            "operation": "DELETE",
            "table": table_name,
            "condition": where_condition
        }
    
    def _split_values(self, values_str):
        """
        Divide una cadena de valores separados por comas, respetando comillas y paréntesis.
        
        Args:
            values_str (str): Cadena de valores a dividir
            
        Returns:
            list: Lista de valores individuales
        """
        values = []
        current = ""
        in_quotes = False
        quote_char = None
        level = 0
        
        for char in values_str + ',':  # Añadir coma al final para capturar el último valor
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
                values.append(current.strip())
                current = ""
            else:
                current += char
        
        return values