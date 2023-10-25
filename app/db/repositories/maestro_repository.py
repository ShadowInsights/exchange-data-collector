from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.maestro import MaestroInstanceModel


async def create_maestro(
    session: AsyncSession, launch_id: UUID
) -> MaestroInstanceModel:
    maestro = MaestroInstanceModel(
        launch_id=launch_id, latest_liveness_time=datetime.now()
    )
    session.add(maestro)
    return maestro


async def update_maestro_liveness_time(
    session: AsyncSession, maestro_id: UUID, commit: bool = True
) -> None:
    maestro = await session.get(MaestroInstanceModel, maestro_id)
    maestro.latest_liveness_time = datetime.now()

    if commit:
        await session.commit()
