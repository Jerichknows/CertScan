from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    rooms = db.relationship('Room', backref='building', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(10), nullable=False, default='green')  # green, yellow, red
    reservations = db.relationship('Reservation', backref='room', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    professors_name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # e.g. Monday, Tuesday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    details = db.Column(db.Text)  # optional
