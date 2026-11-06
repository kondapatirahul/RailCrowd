"""Compare disruption observations across candidate trains for a route."""
from backend.app.modules.incidents.route_recommendations import alternative_trains, recommendation_notice
from backend.app.modules.incidents.impact_forecast import train_historical_signal
from backend.app.modules.incidents.impact import impact_summary_for_train

def compare_train_options(origin, destination, exclude=None, limit=8):
    options = alternative_trains(origin, destination, exclude, limit)
    result = []
    for option in options:
        train = option["train"]
        impact = impact_summary_for_train(train.number)
        history = train_historical_signal(train.number, 30)["history"]
        result.append({"number": train.number, "name": train.name,
            "departure_time": train.departure_time, "arrival_time": train.arrival_time,
            "active_incident_count": impact["count"], "current_reported_impact": impact["level"],
            "historical_signal": history["level"], "historical_report_count": history["count"]})
    result.sort(key=lambda item: (item["active_incident_count"], item["historical_report_count"], item["number"]))
    return {"items": result, "notice": recommendation_notice(),
            "origin": origin.upper(), "destination": destination.upper()}

def compare_explanation(item):
    parts = [f"{item['number']} {item['name']}"]
    parts.append(f"{item['active_incident_count']} active community report(s)")
    parts.append(f"{item['historical_report_count']} historical report(s) in the selected window")
    parts.append("These indicators do not represent official service reliability.")
    return ". ".join(parts)
