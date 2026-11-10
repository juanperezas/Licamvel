"""
Modelos SQLAlchemy que mapean exactamente las 5 tablas de la base 'licamvel'.
"""
from datetime import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Categoria(Base):
    __tablename__ = "categoria"

    ID_categoria: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    tiempo_entrega: Mapped[int] = mapped_column(Integer, nullable=False)

    velas: Mapped[list["Vela"]] = relationship(back_populates="categoria")


class Vela(Base):
    __tablename__ = "vela"

    ID_vela: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_vela: Mapped[str] = mapped_column(String(100), nullable=False)
    precio_vela: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ID_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.ID_categoria"), nullable=False)

    categoria: Mapped["Categoria"] = relationship(back_populates="velas")
    detalles: Mapped[list["DetallePedido"]] = relationship(back_populates="vela")


class Cliente(Base):
    __tablename__ = "cliente"

    ID_cliente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_c: Mapped[str] = mapped_column(String(40), nullable=False)
    apellido_c: Mapped[str] = mapped_column(String(40), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(15), nullable=True)
    correo: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")


class Pedido(Base):
    __tablename__ = "pedido"

    ID_pedido: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_pedido: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    metodo_pago: Mapped[str] = mapped_column(String(30), nullable=False)
    estado_pedido: Mapped[str] = mapped_column(String(40), nullable=False)
    total: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False, default=0)
    ID_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.ID_cliente"), nullable=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")
    detalles: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    ID_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cantidad_velas: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    ID_vela: Mapped[int] = mapped_column(ForeignKey("vela.ID_vela"), nullable=False)
    ID_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.ID_pedido"), nullable=False)

    vela: Mapped["Vela"] = relationship(back_populates="detalles")
    pedido: Mapped["Pedido"] = relationship(back_populates="detalles")