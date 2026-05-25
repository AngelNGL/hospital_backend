from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.usuario import Usuario


def require_role(required_role: str):
    def role_checker(
            usuario_actual: Usuario = Depends(get_current_user),
    ) -> Usuario:
        rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None

        if rol_actual != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso a esta acción",
            )
        return usuario_actual
    return role_checker

def require_any_role(required_roles: list[str]):
    def role_checker(
            usuario_actual: Usuario = Depends(get_current_user),
    ) -> Usuario:
        rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None

        if rol_actual not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso a esta acción",
            )
        return usuario_actual
    return role_checker
