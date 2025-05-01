from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete
from app.models import DataModel


class BaseRepository:
    def __init__(self, db: AsyncSession, model):
        self.db = db
        self.model = model

    async def create(self, obj_data: dict, refresh_fields: list[str] = None):
        obj = self.model(**obj_data)
        self.db.add(obj)
        await self.db.commit()
        if refresh_fields:
            await self.db.refresh(obj, refresh_fields)
        else:
            await self.db.refresh(obj)
        return obj

    async def get_by_id(self, item_id: int):
        result = await self.db.execute(
            select(self.model).where(self.model.id == item_id)
        )
        return result.scalars().first()

    async def get_all(self, limit: int = 10, offset: int = 0):
        result = await self.db.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def update(self, item_id: int, update_data: dict):
        await self.db.execute(
            sqlalchemy_update(self.model)
            .where(self.model.id == item_id)
            .values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(item_id)

    async def delete(self, item_id: int) -> bool:
        result = await self.db.execute(
            sqlalchemy_delete(self.model).where(self.model.id == item_id)
        )
        await self.db.commit()
        return result.rowcount > 0


class DataRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, DataModel)

    async def get_many_by_schema(self, schema_name: str, limit=10, offset=0):
        result = await self.db.execute(
            select(self.model)
            .where(self.model.schema_name == schema_name)
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()
