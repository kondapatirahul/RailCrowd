from datetime import datetime, timedelta, timezone

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote
from backend.app.models.user import User
from backend.app.modules.crowd.verification_service import (
    cast_report_vote,
    find_recent_duplicate,
    get_public_verification_reports,
)


def _seed_report(app, *, status="approved"):
    with app.app_context():
        author = db.session.query(User).filter_by(username="dashboardpassenger").one()
        voter = User(
            username="verificationvoter",
            email="verificationvoter@example.com",
            full_name="Verification Voter",
            role="passenger",
        )
        voter.set_password("StrongPass123")
        db.session.add(voter)
        db.session.flush()
        report = CrowdReport(
            user_id=author.id,
            train_number="12727",
            train_name="Godavari Express",
            from_station="Visakhapatnam",
            to_station="Rajahmundry",
            coach_type="Sleeper",
            crowd_level="High",
            status=status,
        )
        db.session.add(report)
        db.session.commit()
        return report.id, author.id, voter.id


def test_voter_can_confirm_another_passengers_approved_report(dashboard_app):
    report_id, _author_id, voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        result, code = cast_report_vote(
            report_id=report_id, user_id=voter_id, vote_type="confirm"
        )
        assert (result, code) == ("created", 200)
        vote = db.session.query(CrowdReportVote).filter_by(report_id=report_id).one()
        assert vote.vote_type == "confirm"


def test_voter_can_change_feedback_without_duplicate_row(dashboard_app):
    report_id, _author_id, voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        cast_report_vote(report_id=report_id, user_id=voter_id, vote_type="confirm")
        result, code = cast_report_vote(
            report_id=report_id, user_id=voter_id, vote_type="flag"
        )
        assert (result, code) == ("updated", 200)
        votes = db.session.query(CrowdReportVote).filter_by(report_id=report_id).all()
        assert len(votes) == 1
        assert votes[0].vote_type == "flag"


def test_author_cannot_vote_on_own_report(dashboard_app):
    report_id, author_id, _voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        assert cast_report_vote(
            report_id=report_id, user_id=author_id, vote_type="confirm"
        ) == ("own_report", 403)


def test_pending_report_cannot_receive_feedback(dashboard_app):
    report_id, _author_id, voter_id = _seed_report(dashboard_app, status="pending")
    with dashboard_app.app_context():
        assert cast_report_vote(
            report_id=report_id, user_id=voter_id, vote_type="confirm"
        ) == ("not_eligible", 409)


def test_invalid_feedback_type_is_rejected(dashboard_app):
    report_id, _author_id, voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        assert cast_report_vote(
            report_id=report_id, user_id=voter_id, vote_type="maybe"
        ) == ("invalid_vote", 400)


def test_duplicate_detector_matches_same_segment_and_coach(dashboard_app):
    report_id, author_id, _voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        duplicate = find_recent_duplicate(
            user_id=author_id,
            train_number=report.train_number,
            from_station=report.from_station,
            to_station=report.to_station,
            coach_type=report.coach_type,
            now=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        assert duplicate.id == report_id


def test_public_reliability_reports_confirmation_and_flag_counts(dashboard_app):
    report_id, author_id, voter_id = _seed_report(dashboard_app)
    with dashboard_app.app_context():
        another = User(
            username="verificationvoter2",
            email="verificationvoter2@example.com",
            full_name="Second Voter",
            role="passenger",
        )
        another.set_password("StrongPass123")
        db.session.add(another)
        db.session.flush()
        db.session.add_all([
            CrowdReportVote(report_id=report_id, user_id=voter_id, vote_type="confirm"),
            CrowdReportVote(report_id=report_id, user_id=another.id, vote_type="confirm"),
        ])
        db.session.commit()
        items = get_public_verification_reports("12727")
        assert len(items) == 1
        assert items[0]["confirm_count"] == 2
        assert items[0]["flag_count"] == 0
        assert items[0]["reliability"] == "Early feedback"
