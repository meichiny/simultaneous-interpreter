import re
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import HotWordTable, HotWord

hotwords_bp = Blueprint("hotwords", __name__, url_prefix="/api/hotwords")

VALID_WORD_RE = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9 ]+$")


def validate_word(word):
    if not word or not word.strip():
        return "热词不能为空"
    word = word.strip()
    if len(word.encode('utf-8')) > 30:
        return "热词不能超过 30 字节（约 10 个汉字或 30 个字母）"
    if not VALID_WORD_RE.match(word):
        return "热词仅允许中文汉字、英文字母、数字和空格"
    return None


def validate_words(words):
    errors = []
    seen = set()
    valid = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        err = validate_word(w)
        if err:
            errors.append({"word": w, "error": err})
        elif w in seen:
            errors.append({"word": w, "error": "重复热词"})
        else:
            seen.add(w)
            valid.append(w)
    return valid, errors


@hotwords_bp.route("/tables", methods=["GET"])
def get_tables():
    tables = HotWordTable.query.order_by(HotWordTable.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tables])


@hotwords_bp.route("/tables", methods=["POST"])
def create_table():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "词表名称不能为空"}), 400
    table = HotWordTable(name=data["name"])
    db.session.add(table)
    db.session.commit()
    return jsonify(table.to_dict()), 201


@hotwords_bp.route("/tables/<int:table_id>", methods=["PUT"])
def rename_table(table_id):
    table = HotWordTable.query.get_or_404(table_id)
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "新名称不能为空"}), 400
    table.name = data["name"]
    db.session.commit()
    return jsonify(table.to_dict())


@hotwords_bp.route("/tables/<int:table_id>", methods=["DELETE"])
def delete_table(table_id):
    table = HotWordTable.query.get_or_404(table_id)
    db.session.delete(table)
    db.session.commit()
    return jsonify({"message": "词表已删除"})


@hotwords_bp.route("/tables/<int:table_id>/words", methods=["GET"])
def get_words(table_id):
    HotWordTable.query.get_or_404(table_id)
    words = HotWord.query.filter_by(table_id=table_id).order_by(HotWord.id).all()
    return jsonify([w.to_dict() for w in words])


@hotwords_bp.route("/tables/<int:table_id>/words", methods=["POST"])
def add_word(table_id):
    HotWordTable.query.get_or_404(table_id)
    data = request.get_json()
    if not data or not data.get("word"):
        return jsonify({"error": "热词不能为空"}), 400
    word_text = data["word"].strip()
    err = validate_word(word_text)
    if err:
        return jsonify({"error": err}), 400
    existing = HotWord.query.filter_by(word=word_text, table_id=table_id).first()
    if existing:
        return jsonify({"error": "该热词已存在于当前词表中"}), 400
    word = HotWord(word=word_text, table_id=table_id)
    db.session.add(word)
    db.session.commit()
    return jsonify(word.to_dict()), 201


@hotwords_bp.route("/words/<int:word_id>", methods=["DELETE"])
def delete_word(word_id):
    word = HotWord.query.get_or_404(word_id)
    db.session.delete(word)
    db.session.commit()
    return jsonify({"message": "热词已删除"})


@hotwords_bp.route("/words/delete_bulk", methods=["POST"])
def delete_bulk_words():
    data = request.get_json()
    ids = data.get("ids")
    if not ids or not isinstance(ids, list):
        return jsonify({"error": "数据格式无效"}), 400
    num_deleted = HotWord.query.filter(HotWord.id.in_(ids)).delete(
        synchronize_session=False
    )
    db.session.commit()
    return jsonify({"message": f"已删除 {num_deleted} 个热词"})


@hotwords_bp.route("/tables/<int:table_id>/import", methods=["POST"])
def import_words(table_id):
    HotWordTable.query.get_or_404(table_id)

    if request.content_type == "text/plain":
        raw = request.get_data(as_text=True)
        words = [w.strip() for w in raw.split("\n") if w.strip()]
    else:
        data = request.get_json()
        if not data or "words" not in data:
            return jsonify({"error": "请求数据格式无效"}), 400
        words = data["words"]

    valid, errors = validate_words(words)

    existing_words = set(
        w.word
        for w in HotWord.query.filter(
            HotWord.table_id == table_id, HotWord.word.in_(valid)
        ).all()
    )

    filtered = []
    for w in valid:
        if w in existing_words:
            errors.append({"word": w, "error": "重复热词"})
        else:
            filtered.append(w)

    for w in filtered:
        db.session.add(HotWord(word=w, table_id=table_id))
    db.session.commit()

    return jsonify(
        {
            "imported": len(filtered),
            "errors": errors,
            "message": f"成功导入 {len(filtered)} 个热词，{len(errors)} 个失败",
        }
    ), 201 if filtered else 200
