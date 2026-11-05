"""Freshness-weighted crowd summaries based on approved community reports."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import exp
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
LEVEL_SCORE={"Low":1,"Moderate":2,"High":3,"Very High":4}
def crowd_label(score):
    if score < 1.5: return "Low"
    if score < 2.5: return "Moderate"
    if score < 3.5: return "High"
    return "Very High"
def get_train_crowd_summary(train_number):
    now=datetime.now(timezone.utc); cutoff=now-timedelta(hours=6)
    reports=db.session.execute(select(CrowdReport).where(CrowdReport.train_number==str(train_number),CrowdReport.status=="approved",CrowdReport.observed_at>=cutoff).order_by(CrowdReport.observed_at.desc())).scalars().all()
    groups=defaultdict(list)
    for report in reports: groups[report.coach_type].append(report)
    coaches=[]; total_score=0.0; total_weight=0.0
    for coach,rows in sorted(groups.items()):
        score_sum=weight_sum=0.0
        for report in rows:
            observed=report.observed_at
            if observed.tzinfo is None: observed=observed.replace(tzinfo=timezone.utc)
            age=max(0.0,(now-observed).total_seconds()/60); weight=exp(-age/180.0)
            score_sum+=LEVEL_SCORE.get(report.crowd_level,2)*weight; weight_sum+=weight
        score=score_sum/weight_sum if weight_sum else 0
        total_score+=score_sum; total_weight+=weight_sum
        coaches.append({"coach":coach,"level":crowd_label(score),"score":round(score,2),"reports":len(rows)})
    if not reports or not total_weight:
        return {"available":False,"level":None,"reports":0,"confidence":"No recent data","coaches":[],"message":"No approved community reports in the last 6 hours."}
    confidence="Low" if len(reports)<3 else "Medium" if len(reports)<7 else "Higher"
    latest=max(r.observed_at for r in reports if r.observed_at)
    return {"available":True,"level":crowd_label(total_score/total_weight),"score":round(total_score/total_weight,2),"reports":len(reports),"confidence":confidence,"updated_at":latest.isoformat(),"coaches":coaches,"message":"Community estimate from approved reports in the last 6 hours; not official occupancy.","demo_data":all((report.notes or "").startswith("[DEMO SAMPLE]") for report in reports)}
