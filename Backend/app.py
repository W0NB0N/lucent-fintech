from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import base64
import os
from google import genai
from google.genai import types
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import requests

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your-secret-key"  # Change to secure secret

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Widget(db.Model):
    __tablename__ = 'widgets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

class UserWidget(db.Model):
    __tablename__ = 'user_widgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    widget_id = db.Column(db.Integer, db.ForeignKey('widgets.id'), nullable=False)
    visible = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', backref=db.backref('user_widgets', cascade='all, delete-orphan'))
    widget = db.relationship('Widget')

    def to_dict(self):
        return {
            "widget": self.widget.to_dict(),
            "visible": self.visible
        }

circle_members = db.Table('circle_members',
    db.Column('circle_id', db.Integer, db.ForeignKey('circle.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Circle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    members = db.relationship('User', secondary='circle_members', backref='circles')

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circle.id'), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# Utilities
def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload["user_id"]
    except:
        return None

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            abort(401, "Authorization header missing or invalid")
        token = auth_header.split()[1]
        user_id = verify_token(token)
        if not user_id:
            abort(401, "Invalid or expired token")
        return f(user_id, *args, **kwargs)
    return decorated

# Routes

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = generate_token(user.id)
    return jsonify({"token": token})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        token = generate_token(user.id)
        return jsonify({"token": token})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/market-news", methods=["GET"])
def market_news():
    FINNHUB_API_KEY = "d47qqmpr01qk80bi3n30d47qqmpr01qk80bi3n3g"  # Set your key here or use env var
    url = "https://finnhub.io/api/v1/news"
    params = {"category": "general", "token": FINNHUB_API_KEY}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json()[:10]
        result = [{"category": a.get("category"), "headline": a.get("headline"), "source": a.get("source")} for a in articles]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to fetch market news", "details": str(e)}), 500

@app.route("/ai-insights", methods=["POST"])
@auth_required
def ai_insights(user_id):
    data = request.get_json()
    query = data.get("query")
    client = genai.Client(
        api_key="AIzaSyB-OpV4Xb1mCQcVOLZDTJdHWCm5TRNjO_w",
    )

    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"{query}"),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        image_config=types.ImageConfig(
            image_size="1K",
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
    response = {
        "user_id": user_id,
        "query": query,
        "insight": f"Demo insight for query '{chunk.text}'"
    }
    return jsonify(response)

@app.route("/user/<int:user_id>/widgets", methods=["GET"])
@auth_required
def get_user_widgets(user_id_token):
    if user_id_token != int(user_id):
        abort(403, "Unauthorized")

    user_widgets = UserWidget.query.filter_by(user_id=user_id).all()
    if not user_widgets:
        # initialize visibility true for all widgets for this user
        widgets = Widget.query.all()
        for w in widgets:
            uw = UserWidget(user_id=user_id, widget_id=w.id, visible=True)
            db.session.add(uw)
        db.session.commit()
        user_widgets = UserWidget.query.filter_by(user_id=user_id).all()

    return jsonify([uw.to_dict() for uw in user_widgets])


@app.route("/user/<int:user_id>/widgets/<int:widget_id>", methods=["PUT"])
@auth_required
def update_widget_visibility(user_id_token, widget_id):
    if user_id_token != int(user_id):
        abort(403, "Unauthorized")

    data = request.get_json()
    visible = data.get("visible")
    if visible is None:
        return jsonify({"error": "Field 'visible' is required"}), 400

    user_widget = UserWidget.query.filter_by(user_id=user_id, widget_id=widget_id).first()
    if not user_widget:
        return jsonify({"error": "User widget not found"}), 404

    user_widget.visible = bool(visible)
    db.session.commit()

    return jsonify(user_widget.to_dict())

@app.route("/trends/stocks", methods=["GET"])
def get_stock_trends():
    symbols = request.args.get("symbols", "AAPL")  # comma separated
    date_from = request.args.get("date_from")  # YYYY-MM-DD
    date_to = request.args.get("date_to")      # YYYY-MM-DD

    url = f"http://api.marketstack.com/v1/eod"
    params = {
        "access_key": "121c326301e6ac7c44bf8a969f040ebb",
        "symbols": symbols,
        "sort": "DESC",
        "limit": 50
    }
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Failed to fetch stock trends", "details": str(e)}), 500

@app.route("/trends/crypto", methods=["GET"])
def get_crypto_rates():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": "6c8f891817fc47a9a5548a9ffcc3f535",
    }
    params = {
        "start": "1",
        "limit": "10",    # Top 10 cryptos
        "convert": "INR"
    }
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Failed to fetch crypto rates", "details": str(e)}), 500

@app.route("/circles", methods=["POST"])
@auth_required
def create_circle(user_id):
    data = request.get_json()
    name = data.get("name")
    member_ids = data.get("member_ids", [])
    if not name:
        return jsonify({"error": "Circle name is required"}), 400

    circle = Circle(name=name, owner_id=user_id)
    db.session.add(circle)
    db.session.commit()

    # Add members including creator
    members = User.query.filter(User.id.in_(member_ids)).all()
    circle.members = members + [User.query.get(user_id)]
    db.session.commit()

    return jsonify({"circle_id": circle.id, "name": circle.name})

@app.route("/circles", methods=["GET"])
@auth_required
def list_circles(user_id):
    circles = Circle.query.filter(
        (Circle.owner_id == user_id) | 
        (Circle.members.any(id=user_id))
    ).all()
    result = []
    for c in circles:
        result.append({"id": c.id, "name": c.name})
    return jsonify(result)

@app.route("/circles/<int:circle_id>/expenses", methods=["POST"])
@auth_required
def add_expense(user_id, circle_id):
    circle = Circle.query.get(circle_id)
    if not circle or user_id not in [m.id for m in circle.members] + [circle.owner_id]:
        return jsonify({"error": "Not authorized for this circle"}), 403
    data = request.get_json()
    amount = data.get("amount")
    description = data.get("description", "")
    date_str = data.get("date")
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.datetime.utcnow()
    if not amount:
        return jsonify({"error": "Amount is required"}), 400

    expense = Expense(circle_id=circle_id, payer_id=user_id, amount=amount, description=description, date=date)
    db.session.add(expense)
    db.session.commit()
    return jsonify({"expense_id": expense.id})

@app.route("/circles/<int:circle_id>/expenses", methods=["GET"])
@auth_required
def list_expenses(user_id, circle_id):
    circle = Circle.query.get(circle_id)
    if not circle or user_id not in [m.id for m in circle.members] + [circle.owner_id]:
        return jsonify({"error": "Not authorized for this circle"}), 403
    expenses = Expense.query.filter_by(circle_id=circle_id).all()
    result = []
    for e in expenses:
        result.append({
            "id": e.id,
            "payer_id": e.payer_id,
            "amount": e.amount,
            "description": e.description,
            "date": e.date.isoformat()
        })
    return jsonify(result)

@app.route("/circles/<int:circle_id>/expenses/<int:expense_id>", methods=["DELETE"])
@auth_required
def remove_expense(user_id, circle_id, expense_id):
    circle = Circle.query.get(circle_id)
    expense = Expense.query.get(expense_id)
    if not circle or not expense or expense.circle_id != circle_id:
        return jsonify({"error": "Invalid circle or expense"}), 404
    if user_id not in [m.id for m in circle.members] + [circle.owner_id]:
        return jsonify({"error": "Not authorized"}), 403

    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense removed"})

@app.route("/circles/<int:circle_id>/split", methods=["POST"])
@auth_required
def split_expenses(user_id, circle_id):
    circle = Circle.query.get(circle_id)
    if not circle or user_id not in [m.id for m in circle.members] + [circle.owner_id]:
        return jsonify({"error": "Not authorized"}), 403

    data = request.get_json()
    method = data.get("method", "equal")  # equal, custom, dietary
    # Simplified example of equal split
    expenses = Expense.query.filter_by(circle_id=circle_id).all()
    total = sum([e.amount for e in expenses])
    members = [m.id for m in circle.members] + [circle.owner_id]
    splits = {}

    if method == "equal":
        share = total / len(members)
        for m in members:
            splits[m] = share
    elif method == "custom":
        # Custom percentages must be provided in data
        percentages = data.get("percentages")
        if not percentages or sum(percentages.values()) != 100:
            return jsonify({"error": "Invalid percentages"}), 400
        for m in members:
            splits[m] = total * (percentages.get(str(m), 0) / 100)
    elif method == "dietary":
        # Use Gemini AI to compute split
        preferences = data.get("preferences", {})
        query_text = f"Split {total} among {members} based on dietary preferences {preferences}"
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = "gemini-2.5-pro"
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=query_text)])
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config = types.ThinkingConfig(thinking_budget=-1),
            image_config = types.ImageConfig(image_size="1K"),
        )

        splits = {}
        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=generate_content_config
        ):
            # Parse AI response for split amounts (mock here)
            print(chunk.text, end="")
            # Replace with actual parsing logic returning splits dict

        return jsonify({"message": "AI split generated", "response": chunk.text})
    else:
        return jsonify({"error": "Invalid split method"}), 400

    return jsonify({"total": total, "splits": splits})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
                # List of widgets to create
        widget_names = [
            "network",
            "transaction",
            "income",
            "expenditure",
            "investments",
            "savings",
            "goals",
            "credit score",
            "budget",
            "circle",
            "insights"
        ]

        for name in widget_names:
            if not Widget.query.filter_by(name=name).first():
                db.session.add(Widget(name=name))
        db.session.commit()
    app.run(debug=True)
