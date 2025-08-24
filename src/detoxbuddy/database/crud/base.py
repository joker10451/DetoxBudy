"""
@file: base.py
@description: Базовый класс для CRUD операций
@dependencies: sqlalchemy, pydantic
@created: 2024-08-24
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, asc, desc
from pydantic import BaseModel

from detoxbuddy.database.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый класс для CRUD операций"""
    
    def __init__(self, model: Type[ModelType]):
        """
        CRUD объект с методами по умолчанию для Create, Read, Update, Delete (CRUD).
        
        **Параметры**
        * `model`: SQLAlchemy модель
        * `schema`: Pydantic модель (схема) для создания
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Получить запись по ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        order_direction: str = "asc"
    ) -> List[ModelType]:
        """Получить несколько записей"""
        query = db.query(self.model)
        
        # Сортировка
        if order_by and hasattr(self.model, order_by):
            if order_direction.lower() == "desc":
                query = query.order_by(desc(getattr(self.model, order_by)))
            else:
                query = query.order_by(asc(getattr(self.model, order_by)))
        
        return query.offset(skip).limit(limit).all()

    def get_count(self, db: Session, **filters) -> int:
        """Получить количество записей"""
        query = db.query(self.model)
        
        # Применяем фильтры
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        
        return query.count()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Создать новую запись"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Обновить существующую запись"""
        obj_data = db_obj.__dict__
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        """Удалить запись по ID"""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj
    
    def get_by_field(
        self, 
        db: Session, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """Получить запись по определенному полю"""
        if hasattr(self.model, field_name):
            return db.query(self.model).filter(
                getattr(self.model, field_name) == field_value
            ).first()
        return None
    
    def exists(self, db: Session, **filters) -> bool:
        """Проверить существование записи"""
        query = db.query(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        
        return query.first() is not None
