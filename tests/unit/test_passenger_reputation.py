from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote
from backend.app.models.user import User
from backend.app.modules.passenger.services.reputation_service import (
    get_admin_reputation_risks,
    get_passenger_reputation,
    get_reputation_leaderboard,
)


def _seed_reputation(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username="dashboardpassenger").one()
        voter = User(
            username="repvoter",
            email="repvoter@example.com",
            full_name="Reputation Voter",
            role="passenger",
        )
        voter.set_password("StrongPass123")
        db.session.add(voter)
        db.session.flush()
        report = CrowdReport(
            user_id=user.id,
            train_number="12727",
            train_name="Godavari Express",
            from_station="Visakhapatnam",
            to_station="Rajahmundry",
            coach_type="Sleeper",
            crowd_level="High",
            status="approved",
        )
        db.session.add(report)
        db.session.flush()
        db.session.add(CrowdReportVote(
            report_id=report.id, user_id=voter.id, vote_type="confirm"
        ))
        db.session.commit()
        return user.id


def test_reputation_score_uses_approved_reports_and_confirmations(dashboard_app):
    user_id = _seed_reputation(dashboard_app)
    with dashboard_app.app_context():
        metrics = get_passenger_reputation(user_id)
        assert metrics["approved_reports"] == 1
        assert metrics["confirmations"] == 1
        assert metrics["score"] == 7
        assert metrics["trust_level"] == "Contributor"


def test_pending_report_does_not_increase_score(dashboard_app):
    with dashboard_app.app_context():
        user = db.session.query(User).filter_by(username="dashboardpassenger").one()
        db.session.add(CrowdReport(
            user_id=user.id,
            train_number="12727",
            train_name="Godavari Express",
            from_station="Visakhapatnam",
            to_station="Rajahmundry",
            coach_type="Sleeper",
            crowd_level="High",
            status="pending",
        ))
        db.session.commit()
        metrics = get_passenger_reputation(user.id)
        assert metrics["pending_reports"] == 1
        assert metrics["score"] == 0


def test_leaderboard_only_contains_passengers_with_approved_reports(dashboard_app):
    user_id = _seed_reputation(dashboard_app)
    with dashboard_app.app_context():
        leaderboard = get_reputation_leaderboard()
        assert any(entry["user_id"] == user_id for entry in leaderboard)
        assert all(entry["approved_reports"] > 0 for entry in leaderboard)


def test_admin_review_signals_do_not_include_low_flag_accounts(dashboard_app):
    user_id = _seed_reputation(dashboard_app)
    with dashboard_app.app_context():
        assert all(item["user_id"] != user_id for item in get_admin_reputation_risks())


def test_missing_or_admin_user_has_no_passenger_reputation(dashboard_app):
    with dashboard_app.app_context():
        admin = db.session.query(User).filter_by(username="dashboardadmin").one()
        assert get_passenger_reputation(-999) is None
        assert get_passenger_reputation(admin.id) is None
