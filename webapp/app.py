import os, random, requests
from flask import Flask, request, session as flask_session, redirect, url_for


ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo_db")
ODOO_LOGIN = os.getenv("ODOO_LOGIN", "balhorotman@gmail.com")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "root")

# Session HTTP persistante => garde automatiquement le cookie session_id (PDF)
session = requests.Session()


app = Flask(__name__)

app.secret_key = "dev-secret-change-me"
# ----------------------------
# JSON-RPC helpers
# ----------------------------
def rpc(endpoint: str, payload: dict) -> dict:
    """Appel JSON-RPC vers un endpoint Odoo."""
    url = f"{ODOO_URL}{endpoint}"
    r = session.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        # Erreur Odoo JSON-RPC
        raise RuntimeError(data["error"])
    return data

def authenticate() -> dict:
    """
    Endpoint d'authentification:
    POST /web/session/authenticate (PDF)
    Important: session_id dans cookies HTTP.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_LOGIN,
            "password": ODOO_PASSWORD
        },
        "id": random.randint(1, 1_000_000)
    }
    data = rpc("/web/session/authenticate", payload)
    return data["result"]

def call_kw(model: str, method: str, args=None, kwargs=None):
    """
    Endpoint call_kw:
    POST /web/dataset/call_kw (PDF)
    Permet d'appeler search_read, create, write, unlink, etc.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {}
        },
        "id": random.randint(1, 1_000_000)
    }
    data = rpc("/web/dataset/call_kw", payload)
    return data["result"]

def get_cart():
    # stocke { "variant_id": quantity }
    return flask_session.setdefault("cart", {})


@app.get("/")
def home():
    auth_res = authenticate()

    products = call_kw(
        model="product.template",
        method="search_read",
        kwargs={
            "fields": ["id", "name", "list_price", "max_guests", "beds", "pool_available", "product_variant_id"],
            "limit": 20
        }
    )

    cart = get_cart()
    cart_count = sum(cart.values()) if cart else 0

    html = f"""
    <p><a href="/cart">Voir panier ({cart_count})</a></p>
    <h1>Produits (ID={auth_res.get('uid')})</h1>
    <ul>
    """

    for p in products:
        # product_variant_id est souvent un tuple/list: [id, name] ou (id, name)
        variant = p.get("product_variant_id")
        variant_id = None
        if isinstance(variant, (list, tuple)) and len(variant) > 0:
            variant_id = variant[0]

        html += "<li>"
        html += f"{p.get('name')} — {p.get('list_price')}€ — guests: {p.get('max_guests')} — beds: {p.get('beds')} — pool: {p.get('pool_available')}"

        if variant_id:
            html += f"""
            <form method="post" action="/cart/add" style="display:inline; margin-left:10px;">
                <input type="hidden" name="product_id" value="{variant_id}">
                <input type="number" name="qty" value="1" min="1" style="width:60px;">
                <button type="submit">Ajouter</button>
            </form>
            """
        else:
            html += " (Pas de variante commandable)"

        html += "</li>"

    html += "</ul>"
    return html

@app.post("/cart/add")
def cart_add():
    authenticate()
    pid = str(request.form["product_id"])
    qty = int(request.form.get("qty", 1))

    cart = get_cart()
    cart[pid] = cart.get(pid, 0) + qty
    flask_session["cart"] = cart

    return redirect(url_for("home"))

@app.get("/cart")
def cart_view():
    authenticate()
    cart = get_cart()

    html = "<h1>Panier</h1><p><a href='/'>Retour aux produits</a></p>"

    if not cart:
        return html + "<p>Panier vide.</p>"

    product_ids = [int(pid) for pid in cart.keys()]

    products = call_kw(
        "product.product",
        "search_read",
        kwargs={
            "domain": [["id", "in", product_ids]],
            "fields": ["id", "name", "list_price"]
        }
    )
    by_id = {p["id"]: p for p in products}

    total = 0.0
    html += "<ul>"
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        p = by_id.get(pid)
        if not p:
            continue
        line_total = float(p["list_price"]) * int(qty)
        total += line_total
        html += f"<li>{p['name']} — {qty} x {p['list_price']} = {line_total}</li>"
    html += "</ul>"
    html += f"<p><b>Total:</b> {total}</p>"

    html += """
    <h2>Valider la commande</h2>
    <form method="post" action="/checkout">
      <label>Nom client</label><br>
      <input name="customer_name" placeholder="Otman"lab><br><br>
      <label>Email client</label><br>
      <input name="customer_email" placeholder="client@gmail.com"><br><br>
      <button type="submit">Créer une commande Odoo</button>
    </form>
    """
    return html

def get_or_create_partner(name: str, email: str) -> int:
    partners = call_kw(
        "res.partner",
        "search_read",
        kwargs={
            "domain": [["email", "=", email]],
            "fields": ["id"],
            "limit": 1
        }
    )
    if partners:
        return int(partners[0]["id"])

    partner_id = call_kw("res.partner", "create", args=[{"name": name, "email": email}])
    return int(partner_id)

@app.post("/checkout")
def checkout():
    authenticate()
    cart = get_cart()
    if not cart:
        return redirect(url_for("cart_view"))

    name = request.form.get("customer_name", "Client WebApp").strip()
    email = request.form.get("customer_email", "client@example.com").strip()

    partner_id = get_or_create_partner(name, email)

    # créer la commande
    order_id = int(call_kw("sale.order", "create", args=[{"partner_id": partner_id}]))

    # créer les lignes
    for pid_str, qty in cart.items():
        call_kw(
            "sale.order.line",
            "create",
            args=[{
                "order_id": order_id,
                "product_id": int(pid_str),
                "product_uom_qty": int(qty),
            }]
        )

    # vider panier
    flask_session["cart"] = {}

    # lire la commande pour afficher un résumé
    order = call_kw(
        "sale.order",
        "search_read",
        kwargs={
            "domain": [["id", "=", order_id]],
            "fields": ["id", "name", "state", "amount_total"],
            "limit": 1
        }
    )[0]

    return (
        f"<h1>Commande créée</h1>"
        f"<p>Référence: <b>{order['name']}</b></p>"
        f"<p>État: {order['state']}</p>"
        f"<p>Total: {order['amount_total']}</p>"
        f"<p><a href='/'>Retour produits</a></p>"
    )
