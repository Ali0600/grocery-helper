from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Store(Base):
    """A physical store of a chain, resolved for a given postal code."""

    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("chain", "plz", name="uq_store_chain_plz"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chain: Mapped[str] = mapped_column(String(32), index=True)  # "lidl", "rewe"
    name: Mapped[str] = mapped_column(String(128))
    plz: Mapped[str] = mapped_column(String(8), index=True)
    market_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )


class Offer(Base):
    """A single weekly offer. Prices are stored in integer cents to avoid floats."""

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_offer_store_ext"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(256))
    brand: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(48), index=True)
    price_cents: Mapped[int] = mapped_column(Integer)
    regular_price_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_pct: Mapped[Optional[float]] = mapped_column(Float, index=True, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    store: Mapped["Store"] = relationship(back_populates="offers")
