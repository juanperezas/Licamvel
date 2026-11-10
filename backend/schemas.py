"""
Esquemas Pydantic v2 para validación de entrada y salida.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------- Auth / Cliente
class ClienteRegister(BaseModel):
    nombre_c: str = Field(min_length=1, max_length=40)
    apellido_c: str = Field(min_length=1, max_length=40)
    telefono: str | None = Field(default=None, max_length=15)
    correo: EmailStr
    direccion: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=8, max_length=72)  # bcrypt admite máx. 72 bytes


class ClienteLogin(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=72)


class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_cliente: int
    nombre_c: str
    apellido_c: str
    telefono: str | None
    correo: str
    direccion: str | None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------- Categoría
class CategoriaBase(BaseModel):
    nombre_categoria: str = Field(min_length=1, max_length=50)
    tiempo_entrega: int = Field(ge=0, description="Tiempo de entrega en días")


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaResponse(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)

    ID_categoria: int


# ---------------------------------------------------------------- Vela
class VelaBase(BaseModel):
    nombre_vela: str = Field(min_length=1, max_length=100)
    precio_vela: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)
    ID_categoria: int = Field(gt=0)


class VelaCreate(VelaBase):
    pass


class VelaResponse(VelaBase):
    model_config = ConfigDict(from_attributes=True)

    ID_vela: int


# ---------------------------------------------------------------- Pedido
class DetallePedidoCreate(BaseModel):
    ID_vela: int = Field(gt=0)
    cantidad_velas: int = Field(gt=0)


class DetallePedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_detalle: int
    ID_vela: int
    cantidad_velas: int
    precio_unitario: Decimal


class PedidoCreate(BaseModel):
    metodo_pago: str = Field(min_length=1, max_length=30)
    detalles: list[DetallePedidoCreate] = Field(min_length=1)


class PedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_pedido: int
    fecha_pedido: datetime
    metodo_pago: str
    estado_pedido: str
    total: Decimal
    ID_cliente: int
    detalles: list[DetallePedidoResponse]