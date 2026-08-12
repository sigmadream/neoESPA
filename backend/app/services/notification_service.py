from __future__ import annotations

from sqlmodel import Session, select

from ..models.schemas import Notice, Notification, NotificationRead, Submission, SubmissionResult, User


class NotificationService:
    def notify_user(
        self,
        session: Session,
        *,
        user_id: str,
        kind: str,
        title: str,
        message: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            kind=kind,
            title=title,
            message=message,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        session.add(notification)
        return notification

    def notify_all_students(
        self,
        session: Session,
        *,
        kind: str,
        title: str,
        message: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> list[Notification]:
        students = session.exec(
            select(User).where(User.user_group == "student", User.is_active.is_(True))
        ).all()
        return [
            self.notify_user(
                session,
                user_id=student.id,
                kind=kind,
                title=title,
                message=message,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            for student in students
        ]

    def notify_notice_publication(self, session: Session, notice: Notice) -> list[Notification]:
        return self.notify_all_students(
            session,
            kind="notice",
            title=f"새 공지: {notice.title}",
            message=notice.content[:240],
            reference_type="notice",
            reference_id=str(notice.num or 0),
        )

    def notify_submission_graded(
        self,
        session: Session,
        submission: Submission,
        result: SubmissionResult,
    ) -> Notification:
        score = (
            result.manual_total_score
            if result.manual_total_score is not None
            else result.total_score
        )
        return self.notify_user(
            session,
            user_id=submission.user_id,
            kind="grading",
            title=f"채점 완료: 과제 #{submission.homework_num}",
            message=(
                f"제출 #{submission.id or 0}의 채점이 완료되었습니다. "
                f"현재 총점은 {round(score, 2)}점입니다."
            ),
            reference_type="submission",
            reference_id=str(submission.id or 0),
        )

    def list_for_user(self, session: Session, user_id: str, *, limit: int = 20) -> list[NotificationRead]:
        notifications = session.exec(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        ).all()
        return [self.to_read(notification) for notification in notifications]

    def mark_read(self, session: Session, user_id: str, notification_ids: list[int]) -> list[NotificationRead]:
        notifications = session.exec(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids),
            )
        ).all()
        for notification in notifications:
            notification.is_read = True
            session.add(notification)
        session.commit()
        return [self.to_read(notification) for notification in notifications]

    def to_read(self, notification: Notification) -> NotificationRead:
        return NotificationRead(
            id=notification.id or 0,
            kind=notification.kind,
            title=notification.title,
            message=notification.message,
            reference_type=notification.reference_type,
            reference_id=notification.reference_id,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )
