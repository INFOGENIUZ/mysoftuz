from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProgramKeyword(Base):
    """
    SQLAlchemy model representing a search keyword or tag for a program.
    """
    __tablename__ = "program_keywords"
    __table_args__ = (
        UniqueConstraint("program_id", "keyword", name="uq_program_keyword"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    program = relationship("Program", backref="keywords")

    def __repr__(self) -> str:
        return f"<ProgramKeyword program_id={self.program_id} keyword='{self.keyword}'>"
