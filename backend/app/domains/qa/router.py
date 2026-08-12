from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, Text
from sqlmodel import Field, Session, SQLModel, select

from ...api.dependencies import get_current_active_user, get_optional_current_user
from ...core.db import get_session
from ...models.schemas import User
from ..users.serializers import is_staff


class QAPostBase(SQLModel):
    title: str = Field(max_length=200)
    content: str = Field(sa_column=Column(Text, nullable=False))
    is_private: bool = Field(default=False)


class QAPost(QAPostBase, table=True):
    __tablename__ = "qa_posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QAAnswerBase(SQLModel):
    content: str = Field(sa_column=Column(Text, nullable=False))


class QAAnswer(QAAnswerBase, table=True):
    __tablename__ = "qa_answers"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="qa_posts.id", nullable=False)
    author_id: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QAAnswerRead(QAAnswerBase):
    id: int
    post_id: int
    author_id: str
    author_name: Optional[str] = None
    created_at: datetime


class QAPostRead(QAPostBase):
    id: int
    author_id: str
    author_name: Optional[str] = None
    answers: list[QAAnswerRead] = []
    created_at: datetime
    updated_at: datetime


class QAPostCreate(QAPostBase):
    pass


class QAAnswerCreate(QAAnswerBase):
    pass


router = APIRouter()


def _to_post_read(post: QAPost, session: Session) -> QAPostRead:
    author = session.get(User, post.author_id)
    answers_db = session.exec(
        select(QAAnswer).where(QAAnswer.post_id == post.id).order_by(QAAnswer.created_at.asc())
    ).all()
    answers_read = []
    for ans in answers_db:
        ans_author = session.get(User, ans.author_id)
        answers_read.append(
            QAAnswerRead(
                id=ans.id or 0,
                post_id=ans.post_id,
                author_id=ans.author_id,
                author_name=ans_author.name if ans_author else ans.author_id,
                content=ans.content,
                created_at=ans.created_at,
            )
        )
    return QAPostRead(
        id=post.id or 0,
        title=post.title,
        content=post.content,
        is_private=post.is_private,
        author_id=post.author_id,
        author_name=author.name if author else post.author_id,
        answers=answers_read,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.get("/qa", response_model=list[QAPostRead])
def list_qa_posts(
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    posts = session.exec(select(QAPost).order_by(QAPost.id.desc())).all()
    visible: list[QAPostRead] = []
    for post in posts:
        if post.is_private:
            if current_user is None:
                continue
            if post.author_id != current_user.id and not is_staff(current_user):
                continue
        visible.append(_to_post_read(post, session))
    return visible


@router.post("/qa", response_model=QAPostRead, status_code=status.HTTP_201_CREATED)
def create_qa_post(
    payload: QAPostCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    post = QAPost(
        title=payload.title,
        content=payload.content,
        is_private=payload.is_private,
        author_id=current_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return _to_post_read(post, session)


@router.get("/qa/{post_id}", response_model=QAPostRead)
def get_qa_post(
    post_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    post = session.get(QAPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question post not found")
    if post.is_private:
        if current_user is None or (post.author_id != current_user.id and not is_staff(current_user)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question post not found")
    return _to_post_read(post, session)


@router.post("/qa/{post_id}/answers", response_model=QAPostRead)
def add_qa_answer(
    post_id: int,
    payload: QAAnswerCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    post = session.get(QAPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question post not found")
    if post.is_private and (post.author_id != current_user.id and not is_staff(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question post not found")

    answer = QAAnswer(
        post_id=post_id,
        author_id=current_user.id,
        content=payload.content,
        created_at=datetime.now(UTC),
    )
    session.add(answer)
    session.commit()
    return _to_post_read(post, session)
