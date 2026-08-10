import logging
import unicodedata
import difflib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Program, Category, ProgramKeyword, SearchEvent

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Dataclass holding active search multi-filters."""
    category_id: Optional[int] = None
    operating_system: Optional[str] = None
    architecture: Optional[str] = None
    license_type: Optional[str] = None
    min_rating: Optional[float] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    only_free: Optional[bool] = None

    def active_count(self) -> int:
        count = 0
        if self.category_id is not None:
            count += 1
        if self.operating_system is not None:
            count += 1
        if self.architecture is not None:
            count += 1
        if self.license_type is not None:
            count += 1
        if self.min_rating is not None:
            count += 1
        if self.min_size is not None or self.max_size is not None:
            count += 1
        if self.only_free is True:
            count += 1
        return count

    def reset(self):
        self.category_id = None
        self.operating_system = None
        self.architecture = None
        self.license_type = None
        self.min_rating = None
        self.min_size = None
        self.max_size = None
        self.only_free = None


@dataclass
class SearchResult:
    """Dataclass holding search results metadata and program items."""
    programs: List[Program]
    total: int
    page: int
    per_page: int
    total_pages: int
    query: Optional[str] = None
    filters: Optional[SearchFilters] = None
    sort_mode: str = "relevance"


def normalize_search_query(query: Optional[str]) -> str:
    """
    Normalizes search query string:
    - Trims leading/trailing whitespace
    - Replaces consecutive spaces with a single space
    - Converts to lowercase
    - Performs Unicode NFD normalization
    """
    if not query:
        return ""
    clean = " ".join(query.strip().split())
    clean = unicodedata.normalize("NFD", clean)
    clean = "".join(c for c in clean if unicodedata.category(c) != "Mn")
    return clean.lower()


class SearchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_programs(
        self,
        query: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
        sort_mode: str = "relevance",
        page: int = 1,
        per_page: int = 10
    ) -> SearchResult:
        """
        Executes a smart search across active programs, applying multi-filters, keyword matching, and sorting.
        """
        if page < 1:
            page = 1

        norm_q = normalize_search_query(query)
        filters = filters or SearchFilters()

        # Build base SQL query joining Program and Category
        stmt = (
            select(Program)
            .join(Category, Program.category_id == Category.id)
            .where(
                Program.is_active == True,
                Category.is_active == True
            )
        )

        # 1. Query matching (Name, Descriptions, Version, Category, Keywords)
        if norm_q:
            like_pattern = f"%{norm_q}%"

            # Check matching keywords
            kw_stmt = select(ProgramKeyword.program_id).where(ProgramKeyword.keyword.ilike(like_pattern))
            kw_res = await self.session.execute(kw_stmt)
            matched_kw_pids = list(kw_res.scalars().all())

            conditions = [
                Program.name.ilike(like_pattern),
                Program.short_description.ilike(like_pattern),
                Program.description.ilike(like_pattern),
                Program.version.ilike(like_pattern),
                Category.name.ilike(like_pattern)
            ]
            if matched_kw_pids:
                conditions.append(Program.id.in_(matched_kw_pids))

            stmt = stmt.where(or_(*conditions))

        # 2. Multi-Filters Application
        if filters.category_id:
            stmt = stmt.where(Program.category_id == filters.category_id)
        if filters.architecture:
            stmt = stmt.where(Program.architecture.ilike(f"%{filters.architecture}%"))
        if filters.operating_system:
            stmt = stmt.where(Program.operating_system.ilike(f"%{filters.operating_system}%"))
        if filters.license_type:
            stmt = stmt.where(Program.license_type.ilike(f"%{filters.license_type}%"))
        if filters.only_free:
            stmt = stmt.where(or_(Program.license_type.ilike("%free%"), Program.license_type.ilike("%open source%")))
        if filters.min_rating is not None:
            stmt = stmt.where(Program.rating_average >= filters.min_rating)
        if filters.min_size is not None:
            stmt = stmt.where(Program.file_size >= filters.min_size)
        if filters.max_size is not None:
            stmt = stmt.where(Program.file_size <= filters.max_size)

        res = await self.session.execute(stmt)
        matched_programs: List[Program] = list(res.scalars().all())
        total_matched = len(matched_programs)

        # Log zero-result analytics if query was provided and no matches found
        if norm_q and total_matched == 0:
            try:
                event = SearchEvent(query_normalized=norm_q, result_count=0)
                self.session.add(event)
                await self.session.commit()
            except Exception as e:
                logger.warning(f"Failed to log SearchEvent analytics: {e}")

        if total_matched == 0:
            return SearchResult(
                programs=[], total=0, page=1, per_page=per_page, total_pages=1, query=query, filters=filters, sort_mode=sort_mode
            )

        # 3. Sort Modes Application
        def compute_sort_key(program: Program) -> Tuple[int, Any]:
            prog_name_norm = normalize_search_query(program.name)
            cat_name_norm = normalize_search_query(program.category.name if program.category else "")

            # Relevance Rank (if query exists)
            if norm_q:
                if prog_name_norm == norm_q:
                    rank = 1
                elif prog_name_norm.startswith(norm_q):
                    rank = 2
                elif norm_q in prog_name_norm:
                    rank = 3
                elif norm_q in cat_name_norm:
                    rank = 4
                else:
                    rank = 5
            else:
                rank = 1

            if sort_mode == "popular":
                secondary = -program.downloads_count
            elif sort_mode == "new":
                secondary = -int(program.created_at.timestamp()) if program.created_at else 0
            elif sort_mode == "rating":
                secondary = (-program.rating_average, -program.rating_count)
            elif sort_mode == "name":
                secondary = program.name.lower()
            elif sort_mode == "size":
                secondary = program.file_size or 0
            else:  # "relevance"
                secondary = -program.downloads_count

            return (rank, secondary)

        matched_programs.sort(key=compute_sort_key)

        # Calculate pagination
        total_pages = max(1, (total_matched + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page
        paged_programs = matched_programs[offset : offset + per_page]

        return SearchResult(
            programs=paged_programs,
            total=total_matched,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            query=query,
            filters=filters,
            sort_mode=sort_mode
        )

    async def get_search_suggestions(self, query: str, limit: int = 5) -> List[Program]:
        """
        Uses difflib fuzzy matching against all active program names when search yields zero results.
        """
        norm_q = normalize_search_query(query)
        if not norm_q or len(norm_q) < 2:
            return []

        stmt = (
            select(Program)
            .join(Category, Program.category_id == Category.id)
            .where(Program.is_active == True, Category.is_active == True)
        )
        res = await self.session.execute(stmt)
        active_programs = list(res.scalars().all())

        if not active_programs:
            return []

        prog_map = {normalize_search_query(p.name): p for p in active_programs}
        all_names = list(prog_map.keys())

        close_matches = difflib.get_close_matches(norm_q, all_names, n=limit, cutoff=0.5)
        suggestions = [prog_map[name] for name in close_matches if name in prog_map]
        return suggestions
