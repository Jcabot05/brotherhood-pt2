"""Hash de contraseñas y emisión/validación de tokens de acceso.

Cubre las reglas de negocio de la capa de autenticación:

- RN-05: las contraseñas se almacenan siempre con hash, nunca en texto plano
  ni de forma recuperable. Se usa bcrypt, que incorpora una sal aleatoria por
  contraseña y un factor de coste configurable.
- RN-06: el token de sesión tiene una vigencia limitada; una vez expirado,
  obliga a autenticarse de nuevo.

El secreto de firma se lee de la variable de entorno `JWT_SECRETO` y nunca se
escribe en el código ni se versiona.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRETO = os.getenv("JWT_SECRETO")
JWT_ALGORITMO = "HS256"
JWT_MINUTOS_VIGENCIA = int(os.getenv("JWT_MINUTOS_VIGENCIA", "60"))

if not JWT_SECRETO:
    raise RuntimeError(
        "Falta la variable de entorno JWT_SECRETO. "
        "Copie .env.example a .env y defina un secreto de firma."
    )

# bcrypt trunca la entrada a 72 bytes. Rechazar por encima de ese límite evita
# que dos contraseñas distintas con el mismo prefijo resulten equivalentes.
LIMITE_BYTES_CONTRASENA = 72


def hashear_contrasena(contrasena: str) -> str:
    """Devuelve el hash bcrypt de una contraseña (RN-05)."""
    bytes_contrasena = contrasena.encode("utf-8")
    if len(bytes_contrasena) > LIMITE_BYTES_CONTRASENA:
        raise ValueError(
            f"La contraseña no puede superar los {LIMITE_BYTES_CONTRASENA} bytes."
        )
    return bcrypt.hashpw(bytes_contrasena, bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    """Comprueba una contraseña contra su hash almacenado.

    La comparación la hace bcrypt en tiempo constante. Un hash con formato
    inválido devuelve `False` en lugar de propagar la excepción.
    """
    bytes_contrasena = contrasena.encode("utf-8")
    if len(bytes_contrasena) > LIMITE_BYTES_CONTRASENA:
        return False
    try:
        return bcrypt.checkpw(bytes_contrasena, hash_guardado.encode("utf-8"))
    except ValueError:
        return False


def crear_token(id_usuario: int, correo: str, rol: str) -> tuple[str, int]:
    """Emite un token de acceso firmado.

    Devuelve el token y su vigencia en segundos. El identificador del usuario
    viaja en `sub`, que por especificación de JWT es una cadena.
    """
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(minutes=JWT_MINUTOS_VIGENCIA)

    contenido = {
        "sub": str(id_usuario),
        "correo": correo,
        "rol": rol,
        "iat": ahora,
        "exp": expira,
    }
    token = jwt.encode(contenido, JWT_SECRETO, algorithm=JWT_ALGORITMO)
    return token, JWT_MINUTOS_VIGENCIA * 60


def leer_token(token: str) -> dict | None:
    """Valida la firma y la vigencia de un token (RN-06).

    Devuelve su contenido, o `None` si el token es inválido, está expirado o
    fue firmado con otro secreto.
    """
    try:
        return jwt.decode(token, JWT_SECRETO, algorithms=[JWT_ALGORITMO])
    except jwt.PyJWTError:
        return None
