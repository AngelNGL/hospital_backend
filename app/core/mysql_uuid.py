import uuid
from sqlalchemy.types import TypeDecorator, BINARY


class MySQLUUID(TypeDecorator):
    # convierte UUID de Python/string <-> BINARY(16) de MySQL
    # en front/back, ej: "xxxxx-xxx-xxx-..."
    impl = BINARY(16)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Python -> MySQL
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.bytes
        if isinstance(value, str):
            return uuid.UUID(value).bytes
        return value

    def process_result_value(self, value, dialect):
        # MySQL -> Python
        if value is None:
            return None
        return str(uuid.UUID(bytes=value))
