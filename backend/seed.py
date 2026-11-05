"""Create local database and seed clearly labelled demo data."""
from datetime import datetime, timezone
from sqlalchemy import inspect, text
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop
from backend.app.models.crowd_report import CrowdReport
STATIONS=[("VSKP","Visakhapatnam","Visakhapatnam","Andhra Pradesh"),("RJY","Rajahmundry","Rajahmundry","Andhra Pradesh"),("BZA","Vijayawada Junction","Vijayawada","Andhra Pradesh"),("GNT","Guntur Junction","Guntur","Andhra Pradesh"),("SC","Secunderabad Junction","Hyderabad","Telangana"),("TPTY","Tirupati","Tirupati","Andhra Pradesh"),("MAS","Chennai Central","Chennai","Tamil Nadu"),("SBC","KSR Bengaluru","Bengaluru","Karnataka"),("HYB","Hyderabad Deccan","Hyderabad","Telangana"),("NDLS","New Delhi","Delhi","Delhi")]
TRAINS=[("12727","Godavari Express","Express","VSKP","SC"),("12728","Godavari Express","Express","SC","VSKP"),("12740","Vishakha Express","Express","VSKP","SC"),("12741","Vishakha Express","Express","SC","VSKP"),("12805","Janmabhoomi Express","Express","VSKP","SC"),("17225","Amaravati Express","Express","VSKP","HYB"),("12603","Chennai Express","Express","MAS","HYB"),("12608","Lalbagh Express","Express","SBC","MAS"),("12759","Charminar Express","Express","MAS","HYB"),("12839","Howrah Mail","Mail/Express","MAS","NDLS")]
def seed_database():
 app=create_app()
 with app.app_context():
  # Increment 20 added nullable audit columns. Add them safely for existing
  # local databases created from Increment 19 before creating new tables.
  inspector = inspect(db.engine)
  if "crowd_reports" in inspector.get_table_names():
   existing = {column["name"] for column in inspector.get_columns("crowd_reports")}
   additions = {
    "moderated_by_id": "INTEGER",
    "moderated_at": "DATETIME",
    "moderation_note": "VARCHAR(500)",
   }
   with db.engine.begin() as connection:
    for column, sql_type in additions.items():
     if column not in existing:
      connection.execute(text(f"ALTER TABLE crowd_reports ADD COLUMN {column} {sql_type}"))
  db.create_all(); stations={}
  for code,name,city,state in STATIONS:
   row=Station.query.filter_by(code=code).first()
   if row is None: row=Station(code=code,name=name,city=city,state=state); db.session.add(row)
   stations[code]=row
  db.session.flush()
  for number,name,kind,source,destination in TRAINS:
   train=Train.query.filter_by(number=number).first()
   if train is None:
    train=Train(number=number,name=name,train_type=kind,source_station_id=stations[source].id,destination_station_id=stations[destination].id,running_days="Sample catalog record")
    db.session.add(train)
    db.session.flush()
   if not train.stops:
    db.session.add_all([
     TrainStop(train_id=train.id,station_id=stations[source].id,stop_order=1),
     TrainStop(train_id=train.id,station_id=stations[destination].id,stop_order=2),
    ])
  admin=User.query.filter_by(username="admin").first()
  if admin is None: admin=User(username="admin",email="admin@railcrowd.local",full_name="RailCrowd Administrator",role="admin"); admin.set_password("Admin@12345"); db.session.add(admin)
  passenger=User.query.filter_by(username="demo").first()
  if passenger is None: passenger=User(username="demo",email="demo@railcrowd.local",full_name="Demo Passenger",role="passenger"); passenger.set_password("Demo@12345"); db.session.add(passenger)
  db.session.commit()
  if CrowdReport.query.filter(CrowdReport.notes.like("[DEMO SAMPLE]%")).count()==0:
   rows=[("12727","Godavari Express","Visakhapatnam","Rajahmundry","Sleeper","High"),("12727","Godavari Express","Visakhapatnam","Rajahmundry","3A","Moderate"),("12727","Godavari Express","Rajahmundry","Vijayawada Junction","Sleeper","Very High"),("12740","Vishakha Express","Visakhapatnam","Vijayawada Junction","General","High"),("12805","Janmabhoomi Express","Visakhapatnam","Rajahmundry","3A","Low")]
   for number,name,origin,dest,coach,level in rows:
    db.session.add(CrowdReport(user_id=passenger.id,train_number=number,train_name=name,from_station=origin,to_station=dest,coach_type=coach,crowd_level=level,status="approved",observed_at=datetime.now(timezone.utc),notes="[DEMO SAMPLE] Illustrative only; not a real passenger report.",moderated_by_id=admin.id,moderated_at=datetime.now(timezone.utc)))
   db.session.commit()
 print("Database ready. Admin: admin / Admin@12345 | Passenger: demo / Demo@12345")
if __name__=="__main__": seed_database()
