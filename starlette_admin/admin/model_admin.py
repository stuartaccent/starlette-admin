import sqlalchemy as sa
from sqlalchemy.sql.selectable import Select
from starlette.exceptions import HTTPException
from starlette_core.database import database

from starlette_admin.admin import BaseAdmin


class ModelAdmin(BaseAdmin):
    """ The base admin class for sqlalchemy crud operations. """

    model_class: sa.Table
    object_str_function = lambda self: self["id"]

    @classmethod
    def get_default_ordering(cls, qs: Select) -> Select:
        return qs.order_by("id")

    @classmethod
    def get_search_results(cls, qs: Select, term: str) -> Select:
        raise NotImplementedError()

    @classmethod
    def get_ordered_results(
        cls, qs: Select, order_by: str, order_direction: str
    ) -> Select:
        if order_by and order_direction and hasattr(cls.model_class.c, order_by):
            field = getattr(cls.model_class.c, order_by)
            if order_direction == "desc":
                qs = qs.order_by(field.desc())
            else:
                qs = qs.order_by(field)
        return qs

    @classmethod
    async def get_list_objects(cls, request):
        qs = cls.model_class.select()

        # if enabled, call `cls.get_search_results`
        search = request.query_params.get("search", "").strip().lower()
        if cls.search_enabled and search:
            qs = cls.get_search_results(qs, search)

        # if enabled, sort the results
        order_by = request.query_params.get("order_by")
        order_direction = request.query_params.get("order_direction")
        if cls.order_enabled and order_by and order_direction:
            qs = cls.get_ordered_results(qs, order_by, order_direction)
        else:
            qs = cls.get_default_ordering(qs)

        return await database.fetch_all(qs)

    @classmethod
    async def get_object(cls, request):
        id = request.path_params["id"]
        qs = cls.model_class.select().where(cls.model_class.c.id == id)
        obj = await database.fetch_one(qs)
        if not obj:
            raise HTTPException(404)
        obj.__class__.__str__ = cls.object_str_function
        return obj

    @classmethod
    async def do_create(cls, form, request):
        qs = cls.model_class.insert().values(**form.data)
        return await database.execute(qs)

    @classmethod
    async def do_delete(cls, instance, form, request):
        qs = cls.model_class.delete().where(cls.model_class.c.id == instance["id"])
        await database.execute(qs)

    @classmethod
    async def do_update(cls, instance, form, request):
        qs = (
            cls.model_class.update()
            .where(cls.model_class.c.id == instance["id"])
            .values(**form.data)
        )
        return await database.execute(qs)
