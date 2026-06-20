"""Pydantic data models for typing the FastAPI request/responses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer

from spoolman.database import models
from spoolman.math import length_from_weight
from spoolman.settings import SettingDefinition, SettingType


def datetime_to_str(dt: datetime) -> str:
    """Convert a datetime object to a string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


SpoolmanDateTime = Annotated[datetime, PlainSerializer(datetime_to_str)]


class Message(BaseModel):
    message: str = Field()


class SettingResponse(BaseModel):
    value: str = Field(description="Setting value.")
    is_set: bool = Field(description="Whether the setting has been set. If false, 'value' contains the default value.")
    type: SettingType = Field(description="Setting type. This corresponds with JSON types.")


class SettingKV(BaseModel):
    key: str = Field(description="Setting key.")
    setting: SettingResponse = Field(description="Setting value.")

    @staticmethod
    def from_db(definition: SettingDefinition, set_value: str | None) -> "SettingKV":
        """Create a new Pydantic vendor object from a database vendor object."""
        return SettingKV(
            key=definition.key,
            setting=SettingResponse(
                value=set_value if set_value is not None else definition.default,
                is_set=set_value is not None,
                type=definition.type,
            ),
        )


class Vendor(BaseModel):
    id: int = Field(description="Unique internal ID of this vendor.")
    registered: SpoolmanDateTime = Field(description="When the vendor was registered in the database. UTC Timezone.")
    name: str = Field(max_length=64, description="Vendor name.", examples=["Polymaker"])
    comment: str | None = Field(
        None,
        max_length=1024,
        description="Free text comment about this vendor.",
        examples=[""],
    )
    empty_spool_weight: float | None = Field(
        None,
        ge=0,
        description="The empty spool weight, in grams.",
        examples=[140],
    )
    external_id: str | None = Field(
        None,
        max_length=256,
        description=(
            "Set if this vendor comes from an external database. This contains the ID in the external database."
        ),
        examples=["eSun"],
    )
    extra: dict[str, str] = Field(
        description=(
            "Extra fields for this vendor. All values are JSON-encoded data. "
            "Query the /fields endpoint for more details about the fields."
        ),
    )

    @staticmethod
    def from_db(item: models.Vendor) -> "Vendor":
        """Create a new Pydantic vendor object from a database vendor object."""
        return Vendor(
            id=item.id,
            registered=item.registered,
            name=item.name,
            comment=item.comment,
            empty_spool_weight=item.empty_spool_weight,
            external_id=item.external_id,
            extra={field.key: field.value for field in item.extra},
        )


class MultiColorDirection(Enum):
    """Enum for multi-color direction."""

    COAXIAL = "coaxial"
    LONGITUDINAL = "longitudinal"


class Filament(BaseModel):
    id: int = Field(description="Unique internal ID of this filament type.")
    registered: SpoolmanDateTime = Field(description="When the filament was registered in the database. UTC Timezone.")
    name: str | None = Field(
        None,
        max_length=64,
        description=(
            "Filament name, to distinguish this filament type among others from the same vendor."
            "Should contain its color for example."
        ),
        examples=["PolyTerra™ Charcoal Black"],
    )
    vendor: Vendor | None = Field(None, description="The vendor of this filament type.")
    material: str | None = Field(
        None,
        max_length=64,
        description="The material of this filament, e.g. PLA.",
        examples=["PLA"],
    )
    price: float | None = Field(
        None,
        ge=0,
        description="The price of this filament in the system configured currency.",
        examples=[20.0],
    )
    density: float = Field(gt=0, description="The density of this filament in g/cm3.", examples=[1.24])
    diameter: float = Field(gt=0, description="The diameter of this filament in mm.", examples=[1.75])
    weight: float | None = Field(
        None,
        gt=0,
        description="The weight of the filament in a full spool, in grams.",
        examples=[1000],
    )
    spool_weight: float | None = Field(None, ge=0, description="The empty spool weight, in grams.", examples=[140])
    article_number: str | None = Field(
        None,
        max_length=64,
        description="Vendor article number, e.g. EAN, QR code, etc.",
        examples=["PM70820"],
    )
    comment: str | None = Field(
        None,
        max_length=1024,
        description="Free text comment about this filament type.",
        examples=[""],
    )
    settings_extruder_temp: int | None = Field(
        None,
        ge=0,
        description="Overridden extruder temperature, in °C.",
        examples=[210],
    )
    settings_bed_temp: int | None = Field(
        None,
        ge=0,
        description="Overridden bed temperature, in °C.",
        examples=[60],
    )
    color_hex: str | None = Field(
        None,
        min_length=6,
        max_length=8,
        description=(
            "Hexadecimal color code of the filament, e.g. FF0000 for red. Supports alpha channel at the end. "
            "If it's a multi-color filament, the multi_color_hexes field is used instead."
        ),
        examples=["FF0000"],
    )
    multi_color_hexes: str | None = Field(
        None,
        min_length=6,
        description=(
            "Hexadecimal color code of the filament, e.g. FF0000 for red. Supports alpha channel at the end. "
            "Specifying multiple colors separated by commas. "
            "Also set the multi_color_direction field if you specify multiple colors."
        ),
        examples=["FF0000,00FF00,0000FF"],
    )
    multi_color_direction: MultiColorDirection | None = Field(
        None,
        description=("Type of multi-color filament. Only set if the multi_color_hexes field is set."),
        examples=["coaxial", "longitudinal"],
    )
    external_id: str | None = Field(
        None,
        max_length=256,
        description=(
            "Set if this filament comes from an external database. This contains the ID in the external database."
        ),
        examples=["polymaker_pla_polysonicblack_1000_175"],
    )
    extra: dict[str, str] = Field(
        description=(
            "Extra fields for this filament. All values are JSON-encoded data. "
            "Query the /fields endpoint for more details about the fields."
        ),
    )

    @staticmethod
    def from_db(item: models.Filament) -> "Filament":
        """Create a new Pydantic filament object from a database filament object."""
        return Filament(
            id=item.id,
            registered=item.registered,
            name=item.name,
            vendor=Vendor.from_db(item.vendor) if item.vendor is not None else None,
            material=item.material,
            price=item.price,
            density=item.density,
            diameter=item.diameter,
            weight=item.weight,
            spool_weight=item.spool_weight,
            article_number=item.article_number,
            comment=item.comment,
            settings_extruder_temp=item.settings_extruder_temp,
            settings_bed_temp=item.settings_bed_temp,
            color_hex=item.color_hex,
            multi_color_hexes=item.multi_color_hexes,
            multi_color_direction=(
                MultiColorDirection(item.multi_color_direction) if item.multi_color_direction is not None else None
            ),
            external_id=item.external_id,
            extra={field.key: field.value for field in item.extra},
        )


class Spool(BaseModel):
    id: int = Field(description="Unique internal ID of this spool of filament.")
    registered: SpoolmanDateTime = Field(description="When the spool was registered in the database. UTC Timezone.")
    first_used: SpoolmanDateTime | None = Field(
        None,
        description="First logged occurence of spool usage. UTC Timezone.",
    )
    last_used: SpoolmanDateTime | None = Field(
        None,
        description="Last logged occurence of spool usage. UTC Timezone.",
    )
    filament: Filament = Field(description="The filament type of this spool.")
    price: float | None = Field(
        None,
        ge=0,
        description="The price of this spool in the system configured currency.",
        examples=[20.0],
    )
    remaining_weight: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Estimated remaining weight of filament on the spool in grams. "
            "Only set if the filament type has a weight set."
        ),
        examples=[500.6],
    )
    initial_weight: float | None = Field(
        default=None,
        ge=0,
        description=("The initial weight, in grams, of the filament on the spool (net weight)."),
        examples=[1246],
    )
    spool_weight: float | None = Field(
        default=None,
        ge=0,
        description=("Weight of an empty spool (tare weight)."),
        examples=[246],
    )
    used_weight: float = Field(
        ge=0,
        description="Consumed weight of filament from the spool in grams.",
        examples=[500.3],
    )
    remaining_length: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Estimated remaining length of filament on the spool in millimeters."
            " Only set if the filament type has a weight set."
        ),
        examples=[5612.4],
    )
    used_length: float = Field(
        ge=0,
        description="Consumed length of filament from the spool in millimeters.",
        examples=[50.7],
    )
    location: str | None = Field(
        None,
        max_length=64,
        description="Where this spool can be found.",
        examples=["Shelf A"],
    )
    lot_nr: str | None = Field(
        None,
        max_length=64,
        description="Vendor manufacturing lot/batch number of the spool.",
        examples=["52342"],
    )
    comment: str | None = Field(
        None,
        max_length=1024,
        description="Free text comment about this specific spool.",
        examples=[""],
    )
    archived: bool = Field(description="Whether this spool is archived and should not be used anymore.")
    extra: dict[str, str] = Field(
        description=(
            "Extra fields for this spool. All values are JSON-encoded data. "
            "Query the /fields endpoint for more details about the fields."
        ),
    )

    @staticmethod
    def from_db(item: models.Spool) -> "Spool":
        """Create a new Pydantic spool object from a database spool object."""
        filament = Filament.from_db(item.filament)

        # Compute used_weight from usage records
        used_weight = sum(u.used_weight for u in item.usages) if item.usages else 0.0
        used_weight = max(used_weight, 0.0)

        # Compute first_used and last_used from usage records
        first_used = None
        last_used = None
        if item.usages:
            timestamps = [u.timestamp for u in item.usages]
            first_used = min(timestamps)
            last_used = max(timestamps)

        remaining_weight: float | None = None
        remaining_length: float | None = None

        if item.initial_weight is not None:
            remaining_weight = max(item.initial_weight - used_weight, 0)
            remaining_length = length_from_weight(
                weight=remaining_weight,
                density=filament.density,
                diameter=filament.diameter,
            )
        elif filament.weight is not None:
            remaining_weight = max(filament.weight - used_weight, 0)
            remaining_length = length_from_weight(
                weight=remaining_weight,
                density=filament.density,
                diameter=filament.diameter,
            )

        used_length = length_from_weight(
            weight=used_weight,
            density=filament.density,
            diameter=filament.diameter,
        )

        return Spool(
            id=item.id,
            registered=item.registered,
            first_used=first_used,
            last_used=last_used,
            filament=filament,
            price=item.price,
            initial_weight=item.initial_weight,
            spool_weight=item.spool_weight,
            used_weight=used_weight,
            used_length=used_length,
            remaining_weight=remaining_weight,
            remaining_length=remaining_length,
            location=item.location,
            lot_nr=item.lot_nr,
            comment=item.comment,
            archived=item.archived if item.archived is not None else False,
            extra={field.key: field.value for field in item.extra},
        )


class SpoolUsageResponse(BaseModel):
    id: int = Field(description="Unique internal ID of this usage record.")
    spool_id: int = Field(description="The spool that was used.")
    spool_name: str | None = Field(None, description="Display name of the spool (vendor + filament name).")
    printer_id: int | None = Field(None, description="The printer that used the spool, if any.")
    timestamp: SpoolmanDateTime = Field(description="When the usage occurred. UTC Timezone.")
    used_weight: float = Field(description="Weight of filament used in grams. Negative for corrections.")
    used_length: float | None = Field(None, description="Length of filament used in mm. Computed from weight.")

    @staticmethod
    def from_db(item: models.SpoolUsage) -> "SpoolUsageResponse":
        """Create a new Pydantic usage object from a database usage object."""
        used_length: float | None = None
        spool_name: str | None = None

        if item.spool and item.spool.filament:
            fil = item.spool.filament
            used_length = length_from_weight(
                weight=abs(item.used_weight),
                density=fil.density,
                diameter=fil.diameter,
            )
            if item.used_weight < 0:
                used_length = -used_length

            # Build display name
            parts = []
            if fil.vendor and fil.vendor.name:
                parts.append(fil.vendor.name)
            if fil.name:
                parts.append(fil.name)
            elif not parts:
                parts.append(f"Spool #{item.spool_id}")
            spool_name = " - ".join(parts)

        return SpoolUsageResponse(
            id=item.id,
            spool_id=item.spool_id,
            spool_name=spool_name,
            printer_id=item.printer_id,
            timestamp=item.timestamp,
            used_weight=item.used_weight,
            used_length=used_length,
        )


class Printer(BaseModel):
    id: int = Field(description="Unique internal ID of this printer.")
    registered: SpoolmanDateTime = Field(description="When the printer was registered in the database. UTC Timezone.")
    name: str = Field(max_length=64, description="Printer name.", examples=["Prusa MK4"])
    spool: Spool | None = Field(None, description="The spool currently assigned to this printer.")
    comment: str | None = Field(
        None,
        max_length=1024,
        description="Free text comment about this printer.",
        examples=[""],
    )
    external_id: str | None = Field(
        None,
        max_length=256,
        description=(
            "Set if this printer comes from an external database. This contains the ID in the external database."
        ),
    )
    prusaconnect_printer_uuid: str | None = Field(
        None,
        max_length=256,
        description="PrusaConnect printer UUID. Set to enable automatic spool usage tracking via the cloud.",
    )
    extra: dict[str, str] = Field(
        description=(
            "Extra fields for this printer. All values are JSON-encoded data. "
            "Query the /fields endpoint for more details about the fields."
        ),
    )

    @staticmethod
    def from_db(item: models.Printer) -> "Printer":
        """Create a new Pydantic printer object from a database printer object."""
        return Printer(
            id=item.id,
            registered=item.registered,
            name=item.name,
            spool=Spool.from_db(item.spool) if item.spool is not None else None,
            comment=item.comment,
            external_id=item.external_id,
            prusaconnect_printer_uuid=item.prusaconnect_printer_uuid,
            extra={field.key: field.value for field in item.extra},
        )


class Info(BaseModel):
    version: str = Field(examples=["0.7.0"])
    debug_mode: bool = Field(examples=[False])
    automatic_backups: bool = Field(examples=[True])
    data_dir: str = Field(examples=["/home/app/.local/share/spoolman"])
    logs_dir: str = Field(examples=["/home/app/.local/share/spoolman"])
    backups_dir: str = Field(examples=["/home/app/.local/share/spoolman/backups"])
    db_type: str = Field(examples=["sqlite"])
    git_commit: str | None = Field(None, examples=["a1b2c3d"])
    build_date: SpoolmanDateTime | None = Field(None, examples=["2021-01-01T00:00:00Z"])


class HealthCheck(BaseModel):
    status: str = Field(examples=["healthy"])


class BackupResponse(BaseModel):
    path: str = Field(
        default=None,
        description="Path to the created backup file.",
        examples=["/home/app/.local/share/spoolman/backups/spoolman.db"],
    )


class EventType(str, Enum):
    """Event types."""

    ADDED = "added"
    UPDATED = "updated"
    DELETED = "deleted"


class Event(BaseModel):
    """Event."""

    type: EventType = Field(description="Event type.")
    resource: str = Field(description="Resource type.")
    date: SpoolmanDateTime = Field(description="When the event occured. UTC Timezone.")
    payload: BaseModel


class SpoolEvent(Event):
    """Event."""

    payload: Spool = Field(description="Updated spool.")
    resource: Literal["spool"] = Field(description="Resource type.")


class FilamentEvent(Event):
    """Event."""

    payload: Filament = Field(description="Updated filament.")
    resource: Literal["filament"] = Field(description="Resource type.")


class VendorEvent(Event):
    """Event."""

    payload: Vendor = Field(description="Updated vendor.")
    resource: Literal["vendor"] = Field(description="Resource type.")


class PrinterEvent(Event):
    """Event."""

    payload: Printer = Field(description="Updated printer.")
    resource: Literal["printer"] = Field(description="Resource type.")


class SettingEvent(Event):
    """Event."""

    payload: SettingKV = Field(description="Updated setting.")
    resource: Literal["setting"] = Field(description="Resource type.")
