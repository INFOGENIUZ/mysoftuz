from typing import List, Optional, Tuple
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Category, Program
from app.utils.slug import generate_unique_slug


DEFAULT_CATEGORIES = [
    {"name": "Messenger", "icon": "💬", "description": "Messenjerlar va muloqot dasturlari", "sort_order": 1},
    {"name": "Internet", "icon": "🌐", "description": "Brauzerlar va tarmoq dasturlari", "sort_order": 2},
    {"name": "Grafik dizayn", "icon": "🎨", "description": "Rasm tahrirlash va dizayn dasturlari", "sort_order": 3},
    {"name": "Video montaj", "icon": "🎬", "description": "Video va audio montaj vositalari", "sort_order": 4},
    {"name": "Dasturlash", "icon": "💻", "description": "IDE lar va dasturlash vositalari", "sort_order": 5},
    {"name": "Office", "icon": "📄", "description": "Hujjatlar va matn tahrirlovchilari", "sort_order": 6},
    {"name": "Xavfsizlik", "icon": "🛡", "description": "Antiviruslar va xavfsizlik utilitalari", "sort_order": 7},
    {"name": "Gaming", "icon": "🎮", "description": "O'yinlar va kompyuter optimizatorlari", "sort_order": 8},
    {"name": "Utilitalar", "icon": "🔧", "description": "Tizim utilitalari va sozlamalar", "sort_order": 9},
    {"name": "Arxivatorlar", "icon": "🗜", "description": "Fayllarni siqish va arxivlash dasturlari", "sort_order": 10},
    {"name": "Drayverlar", "icon": "📡", "description": "Tizim va qurilma drayverlari", "sort_order": 11},
]


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        image_file_id: Optional[str] = None,
        sort_order: int = 0
    ) -> Category:
        """Creates a new category with a unique slug."""
        if not name or not name.strip():
            raise ValueError("Category name cannot be empty")

        clean_name = name.strip()
        # Check duplicate name
        stmt_dup = select(Category).where(Category.name == clean_name)
        res_dup = await self.session.execute(stmt_dup)
        if res_dup.scalar_one_or_none():
            raise ValueError(f"Category with name '{clean_name}' already exists")

        slug = await generate_unique_slug(self.session, Category, clean_name)
        category = Category(
            name=clean_name,
            slug=slug,
            description=description.strip() if description else None,
            icon=icon.strip() if icon else None,
            image_file_id=image_file_id.strip() if image_file_id else None,
            sort_order=max(0, sort_order),
            is_active=True
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Fetch category by ID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Fetch category by slug."""
        stmt = select(Category).where(Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_category_with_program_count(self, category_id: int) -> Tuple[Optional[Category], int]:
        """Fetch single category along with its program count using an efficient single SQL query."""
        stmt = (
            select(Category, func.count(Program.id))
            .outerjoin(Program, (Category.id == Program.category_id) & (Program.is_active == True))
            .where(Category.id == category_id)
            .group_by(Category.id)
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None, 0
        return row[0], row[1]

    async def get_all_active_categories(self) -> List[Category]:
        """Fetch active categories ordered by sort_order and name."""
        stmt = select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_categories_paginated(self, page: int = 1, page_size: int = 10) -> Tuple[List[Category], int]:
        """Fetches active categories with SQL LIMIT and OFFSET pagination for user panel."""
        if page < 1:
            page = 1

        count_stmt = select(func.count(Category.id)).where(Category.is_active == True)
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        categories = list(res.scalars().all())

        return categories, total_pages

    async def get_admin_categories_paginated(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Tuple[Category, int]], int]:
        """
        Fetches all categories (active & inactive) with program counts using an efficient
        SQL LEFT OUTER JOIN and GROUP BY query (No N+1 query problem).
        """
        if page < 1:
            page = 1

        count_stmt = select(func.count(Category.id))
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Category, func.count(Program.id))
            .outerjoin(Program, (Category.id == Program.category_id) & (Program.is_active == True))
            .group_by(Category.id)
            .order_by(Category.sort_order, Category.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        categories_with_count = res.all()  # Returns list of tuples (Category, program_count)

        return categories_with_count, total_pages

    async def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        image_file_id: Optional[str] = None,
        sort_order: Optional[int] = None,
        unset_description: bool = False,
        unset_icon: bool = False,
        unset_image: bool = False
    ) -> Category:
        """Updates category fields and updates slug if name changed."""
        category = await self.get_category_by_id(category_id)
        if not category:
            raise ValueError(f"Category with id {category_id} not found")

        if name is not None and name.strip():
            clean_name = name.strip()
            if clean_name != category.name:
                # Check duplicate name
                stmt_dup = select(Category).where(Category.name == clean_name, Category.id != category_id)
                res_dup = await self.session.execute(stmt_dup)
                if res_dup.scalar_one_or_none():
                    raise ValueError(f"Category with name '{clean_name}' already exists")

                category.name = clean_name
                category.slug = await generate_unique_slug(self.session, Category, clean_name)

        if unset_description:
            category.description = None
        elif description is not None:
            category.description = description.strip() if description.strip() else None

        if unset_icon:
            category.icon = None
        elif icon is not None:
            category.icon = icon.strip() if icon.strip() else None

        if unset_image:
            category.image_file_id = None
        elif image_file_id is not None:
            category.image_file_id = image_file_id.strip() if image_file_id.strip() else None

        if sort_order is not None:
            category.sort_order = max(0, sort_order)

        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def activate_category(self, category_id: int) -> bool:
        """Activates a category (is_active = True)."""
        category = await self.get_category_by_id(category_id)
        if category:
            category.is_active = True
            await self.session.commit()
            return True
        return False

    async def deactivate_category(self, category_id: int) -> bool:
        """Deactivates a category (is_active = False)."""
        category = await self.get_category_by_id(category_id)
        if category:
            category.is_active = False
            await self.session.commit()
            return True
        return False

    async def delete_category(self, category_id: int) -> bool:
        """
        Deletes a category after verifying that no active or associated programs exist.
        Prevents accidental program deletion (Delete Protection).
        """
        category, prog_count = await self.get_category_with_program_count(category_id)
        if not category:
            raise ValueError(f"Category with id {category_id} not found")

        if prog_count > 0:
            raise ValueError(
                f"Cannot delete category '{category.name}'. It contains {prog_count} associated program(s)."
            )

        await self.session.delete(category)
        await self.session.commit()
        return True

    async def soft_delete_category(self, category_id: int) -> bool:
        """Soft deletes category by setting is_active=False."""
        return await self.deactivate_category(category_id)

    async def seed_default_categories(self) -> List[Category]:
        """Seeds default categories if they do not exist to prevent duplicates."""
        created_list = []
        for item in DEFAULT_CATEGORIES:
            stmt = select(Category).where(Category.name == item["name"])
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                try:
                    cat = await self.create_category(
                        name=item["name"],
                        description=item["description"],
                        icon=item.get("icon"),
                        sort_order=item["sort_order"]
                    )
                    created_list.append(cat)
                except ValueError:
                    pass
        return created_list
