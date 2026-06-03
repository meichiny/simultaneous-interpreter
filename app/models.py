from app.extensions import db
from datetime import datetime, timezone


class TermCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("term_category.id"), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    parent = db.relationship(
        "TermCategory", remote_side=[id], backref="children", lazy=True
    )
    terms = db.relationship(
        "Term", backref="category", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TermCategory {self.name}>"


class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(500), nullable=False, index=True)
    target = db.Column(db.String(500), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("term_category.id"), nullable=False
    )

    def __repr__(self):
        return f"<Term {self.source}>"


class HotWordTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    words = db.relationship(
        "HotWord", backref="table", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "word_count": self.words.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<HotWordTable {self.name}>"


class HotWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(30), nullable=False, index=True)
    table_id = db.Column(db.Integer, db.ForeignKey("hot_word_table.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "word": self.word,
            "table_id": self.table_id,
        }

    def __repr__(self):
        return f"<HotWord {self.word}>"


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer, default=0)
    transcript_path = db.Column(db.String(500))
    status = db.Column(db.String(20), default="recording")
    speak_direction = db.Column(db.String(10))
    listen_direction = db.Column(db.String(10))
