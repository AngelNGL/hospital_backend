from cachetools import TTLCache


# catalogos globales: no dependen de clinica
especialidades_cache = TTLCache(maxsize=10, ttl=600)
parentescos_cache = TTLCache(maxsize=10, ttl=600)
estados_cita_cache = TTLCache(maxsize=10, ttl=600)

# catalogos por clinica:
doctores_cache = TTLCache(maxsize=100, ttl=300)

# disponibilidad: TTL corto porque cambia cuando se crean/cancelan/reporgraman citas
disponibilidad_cache = TTLCache(maxsize=500, ttl=60)

def clear_doctores_cache_for_tenant(id_clinica_tenant: str):
    # limpia el cache de una clinica especifica
    key = f"doctores:{id_clinica_tenant}"
    doctores_cache.pop(key, None)

def clear_disponibilidad_cache_for_doctor(
        id_clinica_tenant: str,
        id_doctor: str,
        fecha: str | None = None,
):
    # limpia cache de disponibilidad, si se pasa fecha solo se borran de esa fecha
    if fecha is not None:
        key = f"disponibilidad:{id_clinica_tenant}:{id_doctor}:{fecha}"
        disponibilidad_cache.pop(key, None)
        return

    prefix = f"disponibilidad:{id_clinica_tenant}:{id_doctor}:"
    keys_to_delete = [
        key for key in disponibilidad_cache.keys()
        if str(key).startswith(prefix)
    ]
    for key in keys_to_delete:
        disponibilidad_cache.pop(key, None)
