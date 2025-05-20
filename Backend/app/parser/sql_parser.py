import sqlparse
import re
import logging
from .base_parser import BaseParser

# Configurar logging
logger = logging.getLogger(__name__)

class SQLParser:
    """
    Parser principal que coordina el análisis de consultas SQL.
    Utiliza parsers especializados para diferentes tipos de consultas.
    """
    
    def __init__(self, sql_query):
        """
        Inicializa el parser con una consulta SQL.
        
        Args:
            sql_query (str): La consulta SQL a analizar
        """
        self.sql_query = sql_query
        self.parsed = sqlparse.parse(sql_query)
        logger.info(f"Consulta SQL recibida para analizar: {sql_query}")
        
        # Los parsers especializados se importarán y configurarán según sea necesario
    
    def get_tokens(self):
        """
        Obtiene los tokens de la consulta SQL.
        
        Returns:
            list: Lista de tokens de la consulta.
        """
        if self.parsed:
            return self.parsed[0].tokens
        return []
    
    def get_query_type(self):
        """
        Determina el tipo de consulta SQL (SELECT, INSERT, UPDATE, DELETE).
        
        Returns:
            str: Tipo de consulta en mayúsculas.
        """
        if not self.parsed:
            return None
            
        # Obtener el tipo directamente de sqlparse
        query_type = self.parsed[0].get_type()
        
        # Si sqlparse no pudo determinar el tipo, hacer un análisis manual
        if not query_type:
            sql_upper = self.sql_query.upper().strip()
            if sql_upper.startswith("SELECT"):
                query_type = "SELECT"
            elif sql_upper.startswith("INSERT"):
                query_type = "INSERT"
            elif sql_upper.startswith("UPDATE"):
                query_type = "UPDATE"
            elif sql_upper.startswith("DELETE"):
                query_type = "DELETE"
            elif sql_upper.startswith("CREATE"):
                query_type = "CREATE"
            elif sql_upper.startswith("DROP"):
                query_type = "DROP"
            elif sql_upper.startswith("ALTER"):
                query_type = "ALTER"
        
        return query_type
    
    def get_table_name(self):
        """
        Obtiene el nombre de la tabla (colección) de la consulta SQL.
        
        Returns:
            str: Nombre de la tabla como cadena (str).
        """
        query_type = self.get_query_type()
        logger.info(f"Tipo de consulta detectado: {query_type}")
        
        # Normalizar la consulta para el análisis
        sql = " " + self.sql_query.strip() + " "
        
        # Patrones de expresiones regulares para diferentes tipos de consultas
        patterns = {
            "SELECT": [
                r"FROM\s+([^\s,;()]+)",  # FROM tabla
                r"FROM\s+([^\s]+)\s+",   # FROM tabla WHERE/GROUP/ORDER/etc
            ],
            "INSERT": [
                r"INSERT\s+INTO\s+([^\s(]+)",  # INSERT INTO tabla
                r"INSERT\s+INTO\s+([^\s]+)\s+", # INSERT INTO tabla VALUES/SELECT
            ],
            "UPDATE": [
                r"UPDATE\s+([^\s,;()]+)",  # UPDATE tabla
                r"UPDATE\s+([^\s]+)\s+",   # UPDATE tabla SET
            ],
            "DELETE": [
                r"DELETE\s+FROM\s+([^\s,;()]+)",  # DELETE FROM tabla
                r"DELETE\s+FROM\s+([^\s]+)\s+",   # DELETE FROM tabla WHERE
            ],
            "CREATE": [
                r"CREATE\s+TABLE\s+([^\s(]+)",  # CREATE TABLE tabla
                r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",  # CREATE TABLE IF NOT EXISTS tabla
            ],
            "DROP": [
                r"DROP\s+TABLE\s+([^\s;]+)",  # DROP TABLE tabla
            ],
            "ALTER": [
                r"ALTER\s+TABLE\s+([^\s;]+)",  # ALTER TABLE tabla
            ]
        }
        
        # Buscar patrones según el tipo de consulta
        if query_type in patterns:
            for pattern in patterns[query_type]:
                match = re.search(pattern, sql, re.IGNORECASE)
                if match:
                    table_name = match.group(1).strip('`[]"\'')
                    # Limpiar cualquier otra sintaxis SQL (como alias)
                    if ' ' in table_name:
                        table_name = table_name.split(' ')[0]
                    logger.info(f"Nombre de tabla extraído con regex: {table_name}")
                    return table_name.lower()
        
        # Si no se encontró con regex, intentar con un enfoque basado en tokens
        try:
            if query_type == "SELECT":
                for i, token in enumerate(self.get_tokens()):
                    if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                        # El siguiente token después de FROM debería ser la tabla
                        j = i + 1
                        while j < len(self.get_tokens()):
                            table_token = self.get_tokens()[j]
                            if table_token.ttype is not sqlparse.tokens.Whitespace:
                                if isinstance(table_token, sqlparse.sql.Identifier):
                                    table_name = table_token.get_real_name()
                                else:
                                    table_name = str(table_token).strip('`[]"\'')
                                logger.info(f"Nombre de tabla extraído con tokens: {table_name}")
                                return table_name.lower()
                            j += 1
        except Exception as e:
            logger.error(f"Error al extraer nombre de tabla con tokens: {e}")
        
        logger.warning("No se pudo determinar el nombre de la tabla")
        return None
    
    def get_where_clause(self):
        """
        Obtiene la cláusula WHERE de una consulta SQL.
        Redirige a where_parser cuando está disponible.
        
        Returns:
            dict: Diccionario con las condiciones.
        """
        # Importación perezosa para evitar dependencias circulares
        from .where_parser import WhereParser
        
        where_parser = WhereParser()
        return where_parser.parse(self.sql_query)
    
    def get_select_fields(self):
        """
        Obtiene los campos a seleccionar de una consulta SELECT.
        Redirige a select_parser cuando está disponible.
        
        Returns:
            list: Lista de campos a seleccionar.
        """
        # Importación perezosa para evitar dependencias circulares
        from .select_parser import SelectParser
        
        select_parser = SelectParser()
        return select_parser.parse(self.sql_query)
    
    def get_insert_values(self):
        """
        Obtiene los valores a insertar de una consulta INSERT INTO.
        Redirige a crud_parser cuando está disponible.
        
        Returns:
            dict: Diccionario con los valores a insertar.
        """
        # Importación perezosa para evitar dependencias circulares
        from .crud_parser import CRUDParser
        
        crud_parser = CRUDParser()
        return crud_parser.parse_insert(self.sql_query)
    
    def get_update_values(self):
        """
        Obtiene los valores a actualizar de una consulta UPDATE.
        Redirige a crud_parser cuando está disponible.
        
        Returns:
            dict: Diccionario con los valores a actualizar.
        """
        # Importación perezosa para evitar dependencias circulares
        from .crud_parser import CRUDParser
        
        crud_parser = CRUDParser()
        return crud_parser.parse_update(self.sql_query)
    
    def get_delete_condition(self):
        """
        Obtiene la condición para eliminar de una consulta DELETE.
        Redirige a crud_parser cuando está disponible.
        
        Returns:
            dict: Diccionario con la condición para eliminar.
        """
        # Importación perezosa para evitar dependencias circulares
        from .crud_parser import CRUDParser
        
        crud_parser = CRUDParser()
        return crud_parser.parse_delete(self.sql_query)

    def get_limit(self):
        """
        Obtiene el valor de LIMIT de una consulta SQL.
        
        Returns:
            int or None: Valor numérico del límite, o None si no hay cláusula LIMIT.
        """
        # Normalizar la consulta
        query = " " + self.sql_query.strip() + " "
        
        # Expresión regular para extraer la cláusula LIMIT
        pattern = r'\sLIMIT\s+(\d+)(?:\s|;|$)'
        match = re.search(pattern, query, re.IGNORECASE)
        
        if match:
            limit_str = match.group(1).strip()
            try:
                limit = int(limit_str)
                logger.info(f"Límite extraído: {limit}")
                return limit
            except ValueError:
                logger.error(f"No se pudo convertir el límite '{limit_str}' a entero")
        
        logger.info("No se encontró cláusula LIMIT en la consulta")
        return None