"""
API REST de 'licamvel' (Tienda de Velas) - FastAPI + SQL Server.
Ejecutar con:  uvicorn main:app --reload
"""
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

import models
import schemas
from database import get_db, settings
from security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session

# Importa tu conexión a la BD y tus modelos existentes
from database import get_db, engine  # Reemplaza 'database' por el nombre de tu archivo de conexión
from models import Cliente            # Reemplaza 'models' por el nombre de tu archivo de modelos

app = FastAPI(title="licamvel API", description="API REST - Tienda de Velas", version="1.0.0")

# ------------------------------------------------------------------ CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],  # "*" no es compatible con credenciales
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-form")


# 1. Tu ID de cliente obtenido de Google Cloud Console
GOOGLE_CLIENT_ID = "321475219574-nt1m7k982re0g9lrs5qthftdvf7cvv0.apps.googleusercontent.com"

# 2. Modelo de datos para la petición de Google
class GoogleAuthRequest(BaseModel):
    id_token: str

# --- AQUÍ AGREGAS EL NUEVO ENDPOINT ---
@app.post("/auth/google", tags=["Auth"])
def login_with_google(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        # Validar el id_token directamente con Google
        id_info = id_token.verify_oauth2_token(
            data.id_token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        email = id_info.get("email")
        nombre = id_info.get("given_name", "Usuario")
        apellido = id_info.get("family_name", "")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El token de Google no incluye correo electrónico."
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token de Google inválido o expirado."
        )

    # Buscar si el cliente ya existe en la base de datos SQL Server
    cliente = db.query(Cliente).filter(Cliente.correo == email).first()

    # Si no existe, crearlo automáticamente (registro transparente)
    if not cliente:
        cliente = Cliente(
            nombre_c=nombre,
            apellido_c=apellido,
            correo=email,
            password=""  # No requiere contraseña al ingresar con Google
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    # Generar el token JWT habitual de la aplicación
    # (Asegúrate de invocar aquí tu función de creación de token, ej: create_access_token)
    access_token = create_access_token(data={"sub": cliente.correo})
    return {"access_token": access_token, "token_type": "bearer"}

# ------------------------------------------------------------------ Dependencias
def get_current_cliente(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Cliente:
    """Obtiene el cliente autenticado a partir del JWT."""
    payload = decode_access_token(token)
    cliente_id = payload.get("sub")
    if cliente_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin sujeto")

    try:
        cliente = db.get(models.Cliente, int(cliente_id))
    except (ValueError, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    if cliente is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cliente no encontrado")
    return cliente


def _db_error(exc: Exception) -> HTTPException:
    """Convierte errores de base de datos en una respuesta 500 genérica (sin filtrar detalles)."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno de base de datos",
    )


# ------------------------------------------------------------------ Raíz
@app.get("/", tags=["Root"])
def root():
    return {"mensaje": "API licamvel operativa"}


# ================================================================== AUTH
@app.post(
    "/auth/register",
    response_model=schemas.ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
)
def register(data: schemas.ClienteRegister, db: Session = Depends(get_db)):
    """Registra un nuevo cliente con contraseña hasheada."""
    try:
        existe = db.scalar(select(models.Cliente).where(models.Cliente.correo == data.correo))
        if existe:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado")

        cliente = models.Cliente(
            nombre_c=data.nombre_c,
            apellido_c=data.apellido_c,
            telefono=data.telefono,
            correo=data.correo,
            direccion=data.direccion,
            password_hash=hash_password(data.password),
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


def _autenticar(correo: str, password: str, db: Session) -> models.Cliente:
    """Valida credenciales y devuelve el cliente o lanza 401."""
    try:
        cliente = db.scalar(select(models.Cliente).where(models.Cliente.correo == correo))
    except SQLAlchemyError as exc:
        raise _db_error(exc)

    if cliente is None or not verify_password(password, cliente.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return cliente


@app.post("/auth/login", response_model=schemas.Token, tags=["Auth"])
def login(data: schemas.ClienteLogin, db: Session = Depends(get_db)):
    """Inicia sesión (JSON) y emite un token JWT."""
    cliente = _autenticar(data.correo, data.password, db)
    token = create_access_token({"sub": str(cliente.ID_cliente), "correo": cliente.correo})
    return schemas.Token(access_token=token)


@app.post("/auth/login-form", response_model=schemas.Token, tags=["Auth"], include_in_schema=True)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login compatible con el botón 'Authorize' de Swagger (username = correo)."""
    cliente = _autenticar(form_data.username, form_data.password, db)
    token = create_access_token({"sub": str(cliente.ID_cliente), "correo": cliente.correo})
    return schemas.Token(access_token=token)


# ================================================================== CATEGORÍAS
@app.post(
    "/categorias",
    response_model=schemas.CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Categorías"],
)
def crear_categoria(data: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    try:
        categoria = models.Categoria(**data.model_dump())
        db.add(categoria)
        db.commit()
        db.refresh(categoria)
        return categoria
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


@app.get("/categorias", response_model=list[schemas.CategoriaResponse], tags=["Categorías"])
def listar_categorias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return db.scalars(
            select(models.Categoria).order_by(models.Categoria.ID_categoria).offset(skip).limit(limit)
        ).all()
    except SQLAlchemyError as exc:
        raise _db_error(exc)


@app.get("/categorias/{categoria_id}", response_model=schemas.CategoriaResponse, tags=["Categorías"])
def obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    try:
        categoria = db.get(models.Categoria, categoria_id)
    except SQLAlchemyError as exc:
        raise _db_error(exc)
    if categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return categoria


@app.put("/categorias/{categoria_id}", response_model=schemas.CategoriaResponse, tags=["Categorías"])
def actualizar_categoria(
    categoria_id: int, data: schemas.CategoriaCreate, db: Session = Depends(get_db)
):
    try:
        categoria = db.get(models.Categoria, categoria_id)
        if categoria is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")

        for campo, valor in data.model_dump().items():
            setattr(categoria, campo, valor)
        db.commit()
        db.refresh(categoria)
        return categoria
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


@app.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categorías"])
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    try:
        categoria = db.get(models.Categoria, categoria_id)
        if categoria is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")

        db.delete(categoria)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoría tiene velas asociadas",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


# ================================================================== VELAS
def _validar_categoria(db: Session, categoria_id: int) -> None:
    """Lanza 400 si la categoría referenciada no existe."""
    if db.get(models.Categoria, categoria_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La categoría con ID {categoria_id} no existe",
        )


@app.post(
    "/velas",
    response_model=schemas.VelaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Velas"],
)
def crear_vela(data: schemas.VelaCreate, db: Session = Depends(get_db)):
    try:
        _validar_categoria(db, data.ID_categoria)
        vela = models.Vela(**data.model_dump())
        db.add(vela)
        db.commit()
        db.refresh(vela)
        return vela
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


@app.get("/velas", response_model=list[schemas.VelaResponse], tags=["Velas"])
def listar_velas(
    skip: int = 0,
    limit: int = 100,
    categoria_id: int | None = None,
    db: Session = Depends(get_db),
):
    try:
        stmt = select(models.Vela).order_by(models.Vela.ID_vela)
        if categoria_id is not None:
            stmt = stmt.where(models.Vela.ID_categoria == categoria_id)
        return db.scalars(stmt.offset(skip).limit(limit)).all()
    except SQLAlchemyError as exc:
        raise _db_error(exc)


@app.get("/velas/{vela_id}", response_model=schemas.VelaResponse, tags=["Velas"])
def obtener_vela(vela_id: int, db: Session = Depends(get_db)):
    try:
        vela = db.get(models.Vela, vela_id)
    except SQLAlchemyError as exc:
        raise _db_error(exc)
    if vela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vela no encontrada")
    return vela


@app.put("/velas/{vela_id}", response_model=schemas.VelaResponse, tags=["Velas"])
def actualizar_vela(vela_id: int, data: schemas.VelaCreate, db: Session = Depends(get_db)):
    try:
        vela = db.get(models.Vela, vela_id)
        if vela is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vela no encontrada")

        _validar_categoria(db, data.ID_categoria)
        for campo, valor in data.model_dump().items():
            setattr(vela, campo, valor)
        db.commit()
        db.refresh(vela)
        return vela
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


@app.delete("/velas/{vela_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Velas"])
def eliminar_vela(vela_id: int, db: Session = Depends(get_db)):
    try:
        vela = db.get(models.Vela, vela_id)
        if vela is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vela no encontrada")

        db.delete(vela)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la vela está asociada a pedidos",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


# ================================================================== PEDIDOS
@app.post(
    "/pedidos",
    response_model=schemas.PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pedidos"],
)
def crear_pedido(
    data: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    cliente: models.Cliente = Depends(get_current_cliente),
):
    """
    Transacción completa:
      1. Consolida líneas repetidas de la misma vela.
      2. Bloquea las filas de vela (UPDLOCK) para evitar sobreventa concurrente.
      3. Verifica existencia y stock de cada vela.
      4. Crea el pedido, inserta el detalle y descuenta el stock.
      5. Confirma todo con un único commit (o revierte ante cualquier error).
    """
    try:
        # 1. Consolidar cantidades por vela (evita duplicados en el detalle)
        cantidades: dict[int, int] = {}
        for item in data.detalles:
            cantidades[item.ID_vela] = cantidades.get(item.ID_vela, 0) + item.cantidad_velas

        # 2. Bloquear y cargar las velas involucradas (en orden para evitar deadlocks)
        ids_ordenados = sorted(cantidades.keys())
        velas = db.scalars(
            select(models.Vela)
            .where(models.Vela.ID_vela.in_(ids_ordenados))
            .order_by(models.Vela.ID_vela)
            .with_for_update()
        ).all()
        velas_por_id = {v.ID_vela: v for v in velas}

        # 3. Validar existencia y stock
        for vela_id in ids_ordenados:
            vela = velas_por_id.get(vela_id)
            if vela is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"La vela con ID {vela_id} no existe",
                )
            if vela.stock < cantidades[vela_id]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente para '{vela.nombre_vela}': "
                        f"disponible {vela.stock}, solicitado {cantidades[vela_id]}"
                    ),
                )

        # 4. Crear pedido
        pedido = models.Pedido(
            metodo_pago=data.metodo_pago,
            estado_pedido="Pendiente",
            total=Decimal("0.00"),
            ID_cliente=cliente.ID_cliente,
        )
        db.add(pedido)
        db.flush()  # Obtiene ID_pedido sin confirmar la transacción

        # 5. Insertar detalle, descontar stock y acumular total
        total = Decimal("0.00")
        for vela_id in ids_ordenados:
            vela = velas_por_id[vela_id]
            cantidad = cantidades[vela_id]
            precio = Decimal(vela.precio_vela)

            db.add(
                models.DetallePedido(
                    ID_pedido=pedido.ID_pedido,
                    ID_vela=vela_id,
                    cantidad_velas=cantidad,
                    precio_unitario=precio,
                )
            )
            vela.stock -= cantidad
            total += precio * cantidad

        pedido.total = total.quantize(Decimal("0.01"))

        # 6. Commit único
        db.commit()

        # Recargar el pedido con sus detalles para la respuesta
        return db.scalars(
            select(models.Pedido)
            .options(selectinload(models.Pedido.detalles))
            .where(models.Pedido.ID_pedido == pedido.ID_pedido)
        ).one()

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_error(exc)


@app.get("/pedidos", response_model=list[schemas.PedidoResponse], tags=["Pedidos"])
def listar_mis_pedidos(
    db: Session = Depends(get_db),
    cliente: models.Cliente = Depends(get_current_cliente),
):
    """Lista los pedidos del cliente autenticado."""
    try:
        return db.scalars(
            select(models.Pedido)
            .options(selectinload(models.Pedido.detalles))
            .where(models.Pedido.ID_cliente == cliente.ID_cliente)
            .order_by(models.Pedido.fecha_pedido.desc())
        ).all()
    except SQLAlchemyError as exc:
        raise _db_error(exc)