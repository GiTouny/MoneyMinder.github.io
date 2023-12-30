import os
import random
import json

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/index_filter", methods=["POST"])
@login_required
def index_filter():
    year = str(request.form.get("year"))
    subscriptions = db.execute("SELECT * FROM subscriptions WHERE user_id = ? LIMIT 2", session["user_id"])
    incomes_query = """
        SELECT
            strftime('%Y', date) AS year,
            strftime('%m', date) AS month,
            types,
            SUM(amount) AS total_amount
        FROM
            transactions
        WHERE
            user_id = ? AND
            types IN ('incomes', 'expenses', 'savings') AND
            strftime('%Y', date) = ? AND
            types = ?
        GROUP BY
            year, month, types;
    """
    chart_incomes = db.execute(incomes_query, session["user_id"], year, "incomes")

    expenses_query = """
    SELECT
        strftime('%Y', date) AS year,
        strftime('%m', date) AS month,
        types,
        SUM(amount) AS total_amount
    FROM
        transactions
    WHERE
        user_id = ? AND
        types IN ('incomes', 'expenses', 'savings') AND
        strftime('%Y', date) = ? AND
        types = ?
    GROUP BY
        year, month, types;
"""
    chart_expenses = db.execute(expenses_query, session["user_id"], year, "expenses")

    savings_query = """
    SELECT
        strftime('%Y', date) AS year,
        strftime('%m', date) AS month,
        types,
        SUM(amount) AS total_amount
    FROM
        transactions
    WHERE
        user_id = ? AND
        types IN ('incomes', 'expenses', 'savings') AND
        strftime('%Y', date) = ? AND
        types = ?
    GROUP BY
        year, month, types;
"""
    chart_savings = db.execute(savings_query, session["user_id"], year, "savings")

    month = str(request.form.get("month"))

    total_incomes_all_time = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ?", "incomes", session["user_id"])[0]['total_incomes']
    total_expenses_all_time = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ?", "expenses", session["user_id"])[0]['total_expenses']

    total_insert_all_time = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "checking", "savings")[0]['total_insert']
    total_withdraw_all_time = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "savings", "checking")[0]['total_withdraw']

    if total_expenses_all_time is None:
        total_expenses_all_time = 0
    if total_incomes_all_time is None:
        total_incomes_all_time = 0

    balance = total_incomes_all_time - total_expenses_all_time

    if total_insert_all_time is None:
        total_insert_all_time = 0
    if total_withdraw_all_time is None:
        total_withdraw_all_time = 0

    total_savings_all_time = total_insert_all_time - total_withdraw_all_time
    checking = balance - total_insert_all_time
    savings_all_time = total_savings_all_time

    # IF MONTH IS NOT SUBMITTED THEN FILTER THE DATA BY THE YEAR FIELD
    if month is None:
        # ------------------------------------------------------- UPDATE SECTION YEARLY ----------------------------------------------------

        total_incomes = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ? AND strftime('%Y', date) = ?", "incomes", session["user_id"], year)[0]['total_incomes']
        total_expenses = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ? AND strftime('%Y', date) = ?", "expenses", session["user_id"], year)[0]['total_expenses']

        if total_expenses is None:
            total_expenses = 0
        if total_incomes is None:
            total_incomes = 0

        balance = total_incomes - total_expenses

        total_insert = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND strftime('%Y', date) = ?", session["user_id"], "checking", "savings", year)[0]['total_insert']
        total_withdraw = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND strftime('%Y', date) = ?", session["user_id"], "savings", "checking", year)[0]['total_withdraw']

        if total_insert is None:
            total_insert = 0
        if total_withdraw is None:
            total_withdraw = 0

        total_savings = total_insert - total_withdraw
        time = f"{year}"

        # -------------------------------------------------------  PLANNING YEARLY  ----------------------------------------------------
        total_incomes_p = db.execute("SELECT SUM(amount) AS total_incomes_planning FROM budget_planning WHERE user_id = ? AND year = ? AND types = ?", session["user_id"], year, "incomes")[0]['total_incomes_planning']
        total_expenses_p = db.execute("SELECT SUM(amount) AS total_expenses_planning FROM budget_planning WHERE user_id = ? AND year = ? AND types = ?", session["user_id"], year, "expenses")[0]['total_expenses_planning']
        total_savings_p = db.execute("SELECT SUM(amount) AS total_savings_planning FROM budget_planning WHERE user_id = ? AND year = ? AND types = ?", session["user_id"], year, "savings")[0]['total_savings_planning']

        if not total_incomes_p:
            total_incomes_p = 0
        if not total_expenses_p:
            total_expenses_p = 0
        if not total_savings_p:
            total_savings_p = 0

        try:
            total_incomes_planning = (total_incomes / total_incomes_p) * 100
            total_expenses_planning = (total_expenses / total_expenses_p) * 100
            total_savings_planning = (total_savings / total_savings_p) * 100
        except ZeroDivisionError:
            total_incomes_planning = 0
            total_expenses_planning = 0
            total_savings_planning = 0

        # -------------------------------------------------------  SPENDING CHART YEARLY  ----------------------------------------------------

        spending_query = """
        SELECT categories.name,
        (SUM(transactions.amount) * 100.0 /
        (SELECT SUM(amount) FROM transactions WHERE user_id = ? AND types = ? AND strftime('%Y', date) = strftime('%Y', ?))) AS category_percentage
        FROM transactions
        JOIN categories ON transactions.category_id = categories.id
        WHERE categories.user_id = ? AND transactions.types = ? AND strftime('%Y', transactions.date) = ?
        GROUP BY categories.name;
    """

        spending_percentage = db.execute(spending_query, session["user_id"], "expenses", year, session["user_id"], "expenses", year)

        labels = [row['name'] for row in spending_percentage]
        data = [row['category_percentage'] for row in spending_percentage]

 #---------------------------------------------------------------------------------------
    if month:
        year_month = "{}-{}".format(year, month.zfill(2))

        total_incomes = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ? AND strftime('%Y-%m', date) = ?", "incomes", session["user_id"], year_month)[0]['total_incomes']
        total_expenses = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ? AND strftime('%Y-%m', date) = ?", "expenses", session["user_id"], year_month)[0]['total_expenses']

        if total_expenses is None:
            total_expenses = 0
        if total_incomes is None:
            total_incomes = 0

        balance = total_incomes - total_expenses

        total_insert = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND strftime('%Y-%m', date) = ?", session["user_id"], "checking", "savings", year_month)[0]['total_insert']
        total_withdraw = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND strftime('%Y-%m', date) = ?", session["user_id"], "savings", "checking", year_month)[0]['total_withdraw']

        if total_insert is None:
            total_insert = 0
        if total_withdraw is None:
            total_withdraw = 0

        total_savings = total_insert - total_withdraw
        time = f"{month}-{year}"

        #---------------------------------------------------------
        month_name = None

        if month == "01":
            month_name = "January"
        elif month == "02":
            month_name = "February"
        elif month == "03":
            month_name = "March"
        elif month == "04":
            month_name = "April"
        elif month == "05":
            month_name = "May"
        elif month == "06":
            month_name = "June"
        elif month == "07":
            month_name = "July"
        elif month == "08":
            month_name = "August"
        elif month == "09":
            month_name = "September"
        elif month == "10":
            month_name = "October"
        elif month == "11":
            month_name = "November"
        elif month == "12":
            month_name = "December"

        total_incomes_p = db.execute("SELECT SUM(amount) AS total_incomes_planning FROM budget_planning WHERE user_id = ? AND month = ? AND year = ? AND types = ?", session["user_id"], month_name, year, "incomes")[0]['total_incomes_planning']
        total_expenses_p = db.execute("SELECT SUM(amount) AS total_expenses_planning FROM budget_planning WHERE user_id = ? AND month = ? AND year = ? AND types = ?", session["user_id"], month_name, year, "expenses")[0]['total_expenses_planning']
        total_savings_p = db.execute("SELECT SUM(amount) AS total_savings_planning FROM budget_planning WHERE user_id = ? AND month = ? AND year = ? AND types = ?", session["user_id"], month_name, year, "savings")[0]['total_savings_planning']

        if not total_incomes_p:
            total_incomes_p = 0
        if not total_expenses_p:
            total_expenses_p = 0
        if not total_savings_p:
            total_savings_p = 0

        try:
            total_incomes_planning = round((total_incomes / total_incomes_p) * 100)
        except ZeroDivisionError:
            total_incomes_planning = 0

        try:
            total_expenses_planning = round((total_expenses / total_expenses_p) * 100)
        except ZeroDivisionError:
            total_expenses_planning = 0

        try:
            total_savings_planning = round((total_savings / total_savings_p) * 100)
        except ZeroDivisionError:
            total_savings_planning = 0

    #------------------------------------------------------
        spending_query = """
        SELECT
            categories.name,
            (SUM(transactions.amount) * 100.0 /
            (SELECT SUM(amount)
            FROM transactions
            WHERE user_id = ? AND types = ? AND strftime('%Y-%m', date) = ?)) AS category_percentage
        FROM transactions
        JOIN categories ON transactions.category_id = categories.id
        WHERE categories.user_id = ? AND transactions.types = ? AND strftime('%Y-%m', transactions.date) = ?
        GROUP BY categories.name;

    """

        spending_percentage = db.execute(spending_query, session["user_id"], "expenses", year_month, session["user_id"], "expenses", year_month)

        labels = [row['name'] for row in spending_percentage]
        data = [row['category_percentage'] for row in spending_percentage]

    recents = db.execute("SELECT transactions.id, transactions.name, transactions.types, transactions.account, transactions.date, transactions.amount, categories.name AS category_name FROM transactions JOIN categories ON transactions.category_id = categories.id WHERE categories.user_id = ? ORDER BY transactions.date DESC LIMIT 3", session["user_id"])
    return render_template("index.html", total_incomes=total_incomes, total_expenses=total_expenses, total_savings=total_savings, checking=checking, time=time, recents=recents, subscriptions=subscriptions, total_incomes_planning=total_incomes_planning, total_expenses_planning=total_expenses_planning, total_savings_planning=total_savings_planning, labels=labels, data=data, chart_incomes=chart_incomes, chart_expenses=chart_expenses, chart_savings=chart_savings, savings_all_time=savings_all_time)


@app.route("/", methods=["GET"])
@login_required
def index():
# ------------------------------------------------------- UPDATE SECTION ALL TIME ----------------------------------------------------

    total_incomes = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ?", "incomes", session["user_id"])[0]['total_incomes']
    total_expenses = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ?", "expenses", session["user_id"])[0]['total_expenses']

    total_insert = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "checking", "savings")[0]['total_insert']
    total_withdraw = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "savings", "checking")[0]['total_withdraw']

    if total_expenses is None:
        total_expenses = 0
    if total_incomes is None:
        total_incomes = 0

    balance = total_incomes - total_expenses

    if total_insert is None:
        total_insert = 0
    if total_withdraw is None:
        total_withdraw = 0

    total_savings = total_insert - total_withdraw
    checking = balance - total_insert
    savings_all_time = total_savings

    time = "All Time"
    recents = db.execute("SELECT transactions.id, transactions.name, transactions.types, transactions.account, transactions.date, transactions.amount, categories.name AS category_name FROM transactions JOIN categories ON transactions.category_id = categories.id WHERE categories.user_id = ? ORDER BY transactions.date DESC LIMIT 3", session["user_id"])

# ------------------------------------------------------- SUBSCRIPTIONS  ----------------------------------------------------
    loop_each_subscription()
    subscriptions = db.execute("SELECT * FROM subscriptions WHERE user_id = ? LIMIT 2", session["user_id"])

# -------------------------------------------------------  PLANNING ALL TIME  ----------------------------------------------------
    total_incomes_planning = 0
    total_expenses_planning = 0
    total_savings_planning = 0

# -------------------------------------------------------  SPENDING CHART ALL TIME  ----------------------------------------------------
    spending_query = """
    SELECT categories.name,
       (SUM(transactions.amount) * 100.0 /
       (SELECT SUM(amount) FROM transactions WHERE user_id = ? AND types = ?)) AS category_percentage
    FROM transactions
    JOIN categories ON transactions.category_id = categories.id
    WHERE categories.user_id = ? AND transactions.types = ?
    GROUP BY categories.name;
"""

    spending_percentage = db.execute(spending_query, session["user_id"], "expenses", session["user_id"], "expenses")

    # Extract data from spending_percentage
    labels = [row['name'] for row in spending_percentage]
    data = [row['category_percentage'] for row in spending_percentage]

# -------------------------------------------------------  BAR CHART THIS YEAR  ----------------------------------------------------

    current_year = str(date.today().year)
    year = request.form.get("year", default=current_year)

    incomes_query = """
        SELECT
            strftime('%Y', date) AS year,
            strftime('%m', date) AS month,
            types,
            SUM(amount) AS total_amount
        FROM
            transactions
        WHERE
            user_id = ? AND
            types IN ('incomes', 'expenses', 'savings') AND
            strftime('%Y', date) = ? AND
            types = ?
        GROUP BY
            year, month, types;
    """
    chart_incomes = db.execute(incomes_query, session["user_id"], year, "incomes")

    expenses_query = """
    SELECT
        strftime('%Y', date) AS year,
        strftime('%m', date) AS month,
        types,
        SUM(amount) AS total_amount
    FROM
        transactions
    WHERE
        user_id = ? AND
        types IN ('incomes', 'expenses', 'savings') AND
        strftime('%Y', date) = ? AND
        types = ?
    GROUP BY
        year, month, types;
"""
    chart_expenses = db.execute(expenses_query, session["user_id"], year, "expenses")

    savings_query = """
    SELECT
        strftime('%Y', date) AS year,
        strftime('%m', date) AS month,
        types,
        SUM(amount) AS total_amount
    FROM
        transactions
    WHERE
        user_id = ? AND
        types IN ('incomes', 'expenses', 'savings') AND
        strftime('%Y', date) = ? AND
        types = ?
    GROUP BY
        year, month, types;
"""
    chart_savings = db.execute(savings_query, session["user_id"], year, "savings")

    return render_template("index.html", total_incomes=total_incomes, total_expenses=total_expenses, total_savings=total_savings, checking=checking, time=time, recents=recents, subscriptions=subscriptions, total_incomes_planning=total_incomes_planning, total_expenses_planning=total_expenses_planning, total_savings_planning=total_savings_planning, labels=labels, data=data, chart_incomes=chart_incomes, chart_expenses=chart_expenses, chart_savings=chart_savings, savings_all_time=savings_all_time)

# --------------------------------------------------------- UPDATING -----------------------------------------------------
@app.route("/add_category", methods=["POST"])
@login_required
def add_category():
    name = request.form.get("name")
    action = request.form.get("action")
    types = "add_category"
    if not name:
        return render_template("update.html", error="Please provide a category")
    if name.isdigit():
        return render_template("update.html", error="Please enter a valid category")

    category_list = db.execute("SELECT name FROM categories WHERE user_id = ?", session["user_id"])
    category_name = [category['name'].lower() for category in category_list]

    if action == "Add Category":
        if name.lower() not in category_name:
            db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", name, types, session['user_id'])
        else:
            return render_template("update.html", error="Existed category")
    else:
        if name.lower() in category_name:
            db.execute("UPDATE categories SET is_deleted = ? WHERE id = (SELECT id FROM categories WHERE name = ? AND user_id = ?)", 1, name, session["user_id"])
        else:
            return render_template("update.html", error="This category is not existed")
    return redirect("/update")

@app.route("/update_input_form", methods=["POST"])
@login_required
def update_input_form():
    """Buy shares of stock"""
    # CHECKING FOR FULL INFORMATIONS FOR INPUT FORM
    name = request.form.get("name")
    if not name:
        return render_template("update.html", error="Please provide name")

    financial_transactions = request.form.get("financial-transactions")
    if not financial_transactions:
        return render_template("update.html", error="Please provide types")

    account = request.form.get("account")
    if not account:
        return render_template("update.html", error="Please provide account types")

    date = request.form.get("date")
    if not date:
        return render_template("update.html", error="Please provide date")

    categories = request.form.get("categories")
    if not categories:
        return render_template("update.html", error="Please provide categories")

    category_list = db.execute("SELECT name FROM categories WHERE user_id = ?", session["user_id"])
    category_name = [category['name'] for category in category_list]

    if categories not in category_name:
        return render_template("update.html", error="Invalid categories")

    amount = request.form.get("amount")
    if not amount:
        return render_template("update.html", error="Please provide amount")

    # WORKING ON THE LOGIC
    category_id = db.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", categories, session["user_id"])[0]['id']

    db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, financial_transactions, account, date, category_id, amount)

    return redirect("/update")

@app.route("/update_transfers_form", methods=["POST"])
@login_required
def update_transfers_form():
    from_ = request.form.get("from")
    to_ = request.form.get("to")
    amount = request.form.get("amount")
    date = request.form.get("date")

    db.execute("INSERT INTO transfers (user_id, from_, to_, date, amount) VALUES (?, ?, ?, ?, ?)", session["user_id"], from_, to_, date, amount)

    return redirect("/update")


@app.route("/update", methods=["GET"])
@login_required
def update():
    category_list = db.execute("SELECT name FROM categories WHERE user_id = ? AND is_deleted = ?", session["user_id"], 0)
    transactions = db.execute("SELECT transactions.id, transactions.name, transactions.types, transactions.account, transactions.date, transactions.amount, categories.name AS category_name FROM transactions JOIN categories ON transactions.category_id = categories.id WHERE categories.user_id = ? LIMIT 10", session["user_id"])
    total_incomes = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ?", "incomes", session["user_id"])[0]['total_incomes']
    total_expenses = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ?", "expenses", session["user_id"])[0]['total_expenses']

    transfers = db.execute("SELECT * FROM transfers WHERE user_id = ? LIMIT 10", session["user_id"])
    total_insert = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "checking", "savings")[0]['total_insert']
    total_withdraw = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ?", session["user_id"], "savings", "checking")[0]['total_withdraw']

    if total_expenses is None:
        total_expenses = 0
    if total_incomes is None:
        total_incomes = 0

    balance = total_incomes - total_expenses

    if total_insert is None:
        total_insert = 0
    if total_withdraw is None:
        total_withdraw = 0

    total_savings = total_insert - total_withdraw

    checking = balance - total_insert
    savings = total_savings
    db.execute("UPDATE users SET checking = ?, savings = ? WHERE id = ?", checking, savings, session["user_id"])
    return render_template("update.html", category_list=category_list, transactions=transactions, total_incomes=total_incomes, total_expenses=total_expenses, transfers=transfers, total_savings=total_savings, balance=balance)

@app.route("/delete_transactions", methods=["POST"])
@login_required
def delete_transactions():
    id = request.form.get("transactions_id")
    db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", id, session["user_id"])
    return redirect("/update")

@app.route("/delete_transfers", methods=["POST"])
@login_required
def delete_transfers():
    id = request.form.get("transfers_id")
    db.execute("DELETE FROM transfers WHERE id = ? AND user_id = ?", id, session["user_id"])
    return redirect("/update")

@app.route("/update_filter", methods=["POST"])
@login_required
def update_filter():
    date = request.form.get("date_filter")
    transactions = db.execute("SELECT transactions.id, transactions.name, transactions.types, transactions.account, transactions.date, transactions.amount, categories.name AS category_name FROM transactions JOIN categories ON transactions.category_id = categories.id WHERE categories.user_id = ? AND transactions.date = ?", session["user_id"], date)
    transfers = db.execute("SELECT * FROM transfers WHERE user_id = ? AND date = ?", session["user_id"], date)
    category_list = db.execute("SELECT name FROM categories WHERE user_id = ?", session["user_id"])

    total_incomes = db.execute("SELECT SUM(amount) AS total_incomes FROM transactions WHERE types = ? AND user_id = ? AND date = ?", "incomes", session["user_id"], date)[0]['total_incomes']
    total_expenses = db.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE types = ? AND user_id = ? AND date = ?", "expenses", session["user_id"], date)[0]['total_expenses']

    if total_expenses is None:
        total_expenses = 0
    if total_incomes is None:
        total_incomes = 0

    balance = total_incomes - total_expenses


    total_insert = db.execute("SELECT SUM(amount) AS total_insert FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND date = ?", session["user_id"], "checking", "savings", date)[0]['total_insert']
    total_withdraw = db.execute("SELECT SUM(amount) AS total_withdraw FROM transfers WHERE user_id = ? AND from_ = ? AND to_ = ? AND date = ?", session["user_id"], "savings", "checking", date)[0]['total_withdraw']

    if total_insert is None:
        total_insert = 0
    if total_withdraw is None:
        total_withdraw = 0

    total_savings = total_insert - total_withdraw

    return render_template("update.html", transactions=transactions, balance=balance, total_savings=total_savings, transfers=transfers, category_list=category_list, total_incomes=total_incomes, total_expenses=total_expenses)

# --------------------------------------------------------- END OF UPDATING -----------------------------------------------------

# --------------------------------------------------------- SUBSCRIPTIONS -----------------------------------------------------
def update_subscription(today, next_due, interval, name, account, category_id, amount):
    if interval == "weekly":
        while today > next_due:
            db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, "subscriptions", account, next_due, category_id, amount)
            next_due = next_due + timedelta(weeks=1)
            next_due_new = next_due + timedelta(weeks=1)
            db.execute("UPDATE subscriptions SET date = ?, next_due = ? WHERE user_id = ?", next_due, next_due_new, session["user_id"])

    elif interval == "monthly":
        while today > next_due:
            db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, "subscriptions", account, next_due, category_id, amount)
            next_due = next_due + relativedelta(months=1)
            next_due_new = next_due + relativedelta(months=1)
            db.execute("UPDATE subscriptions SET date = ?, next_due = ? WHERE user_id = ?", next_due, next_due_new, session["user_id"])

    elif interval == "quarterly":
        while today > next_due:
            db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, "subscriptions", account, next_due, category_id, amount)
            next_due = next_due + relativedelta(months=3)
            next_due_new = next_due + relativedelta(months=3)
            db.execute("UPDATE subscriptions SET date = ?, next_due = ? WHERE user_id = ?", next_due, next_due_new, session["user_id"])

    elif interval == "half_yearly":
        while today > next_due:
            db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, "subscriptions", account, next_due, category_id, amount)
            next_due = next_due + relativedelta(months=6)
            next_due_new = next_due + relativedelta(months=6)
            db.execute("UPDATE subscriptions SET date = ?, next_due = ? WHERE user_id = ?", next_due, next_due_new, session["user_id"])

    elif interval == "annually":
        while today > next_due:
            db.execute("INSERT INTO transactions (user_id, name, types, account, date, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, "subscriptions", account, next_due, category_id, amount)
            next_due = next_due + relativedelta(years=1)
            next_due_new = next_due + relativedelta(years=1)
            db.execute("UPDATE subscriptions SET date = ?, next_due = ? WHERE user_id = ?", next_due, next_due_new, session["user_id"])

def loop_each_subscription():
    subscriptions = db.execute("SELECT * FROM subscriptions WHERE user_id = ?", session["user_id"])
    today = date.today()
    for subscription in subscriptions:
        next_due = datetime.strptime(subscription['next_due'], "%Y-%m-%d").date()
        update_subscription(today, next_due, subscription['interval'], subscription['name'], subscription['account'], subscription['category_id'], subscription['amount'])

@app.route("/subscriptions_input_form", methods=["POST"])
@login_required
def subscriptions_input_form():
    name = request.form.get("name")
    account = request.form.get("account")
    date = datetime.strptime(request.form.get("date"), "%Y-%m-%d")
    interval = request.form.get("interval")
    categories = request.form.get("categories")
    amount = request.form.get("amount")

    category_id = db.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", categories, session["user_id"])[0]['id']

    if interval == "weekly":
        next_due = date + timedelta(weeks=1)
    if interval == "monthly":
        next_due = date + relativedelta(months=1)
    if interval == "quarterly":
        next_due = date + relativedelta(months=3)
    if interval == "half_yearly":
        next_due = date + relativedelta(months=6)
    if interval == "annually":
        next_due = date + relativedelta(years=1)
    next_due = next_due.date()

    db.execute("INSERT INTO subscriptions (user_id, name, account, date, interval, next_due, category_id, amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", session["user_id"], name, account, date, interval, next_due, category_id, amount)
    return redirect("/subscriptions")

@app.route("/delete_subscriptions", methods=["POST"])
@login_required
def delete_subscriptions():
    id = request.form.get("subscriptions_id")
    db.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", id, session["user_id"])
    return redirect("/subscriptions")

@app.route("/subscriptions", methods=["GET"])
@login_required
def subscriptions():
    category_list = db.execute("SELECT name FROM categories WHERE user_id = ? AND is_deleted = ?", session["user_id"], 0)
    subscriptions_ = db.execute("SELECT * FROM subscriptions WHERE user_id = ?", session["user_id"])
    return render_template("subscriptions.html", category_list=category_list, subscriptions=subscriptions_)

# --------------------------------------------------------- END OF SUBSCRIPTIONS -----------------------------------------------------

# --------------------------------------------------------- PLANNING -----------------------------------------------------------------
@app.route("/planning_form", methods=["POST"])
@login_required
def planning_form():
    categories = request.form.get("categories")
    types = request.form.get("types")
    amount = request.form.get("amount")
    month = request.form.get("month")
    year = request.form.get("year")

    category_id = db.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", categories, session["user_id"])[0]['id']

    db.execute("INSERT INTO budget_planning (user_id, category_id, types, month, year, amount) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], category_id, types, month, year, amount)
    return redirect("/planning")

@app.route("/planning", methods=["GET"])
@login_required
def planning():
    category_list = db.execute("SELECT name FROM categories WHERE user_id = ? AND is_deleted = ?", session["user_id"], 0)
    plannings = db.execute("SELECT budget_planning.id, budget_planning.month, budget_planning.year, budget_planning.types, budget_planning.amount, budget_planning.month, categories.name AS category_name FROM budget_planning JOIN categories ON budget_planning.category_id = categories.id WHERE categories.user_id = ?", session["user_id"])

    current_year = str(date.today().year)
    selected_year = request.form.get("year", default=current_year)
    total_incomes = {}
    total_expenses = {}
    total_savings = {}

    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    for month in months:
        query = """
        SELECT
            SUM(CASE WHEN types = 'incomes' THEN amount ELSE 0 END) AS total_incomes,
            SUM(CASE WHEN types = 'expenses' THEN amount ELSE 0 END) AS total_expenses,
            SUM(CASE WHEN types = 'savings' THEN amount ELSE 0 END) AS total_savings
        FROM budget_planning
        WHERE month = ? AND user_id = ? AND year = ?
    """
        result = db.execute(query, month, session["user_id"], selected_year)[0]
        if result:
            total_incomes[month] = result['total_incomes'] or 0
            total_expenses[month] = result['total_expenses'] or 0
            total_savings[month] = result['total_savings'] or 0
        else:
            # Handle the case when there's no result for the given month
            total_incomes[month] = 0
            total_expenses[month] = 0
            total_savings[month] = 0

    return render_template("planning.html", category_list=category_list, plannings=plannings, total_incomes=total_incomes, total_expenses=total_expenses, total_savings=total_savings, selected_year=selected_year)

@app.route("/delete_planning", methods=["POST"])
@login_required
def delete_planning():
    id = request.form.get("planning_id")
    db.execute("DELETE FROM budget_planning WHERE id = ? AND user_id = ?", id, session["user_id"])
    return redirect("/planning")

@app.route("/planning_filter", methods=["POST"])
@login_required
def planning_filter():
    year = str(request.form.get("year"))
    if not year:
        return redirect("/planning")
    selected_year = year
    category_list = db.execute("SELECT name FROM categories WHERE user_id = ?", session["user_id"])
    plannings = db.execute("SELECT budget_planning.id, budget_planning.month, budget_planning.year, budget_planning.types, budget_planning.amount, categories.name AS category_name FROM budget_planning JOIN categories ON budget_planning.category_id = categories.id WHERE categories.user_id = ? AND budget_planning.year = ?", session["user_id"], year)

    total_incomes = {}
    total_expenses = {}
    total_savings = {}

    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    for month in months:
        total_incomes[month] = 0
        total_expenses[month] = 0
        total_savings[month] = 0

    for month in months:
        query = """
        SELECT
            SUM(CASE WHEN types = 'incomes' THEN amount ELSE 0 END) AS total_incomes,
            SUM(CASE WHEN types = 'expenses' THEN amount ELSE 0 END) AS total_expenses,
            SUM(CASE WHEN types = 'savings' THEN amount ELSE 0 END) AS total_savings
        FROM budget_planning
        WHERE month = ? AND user_id = ? AND year = ?
        """
        result = db.execute(query, month, session["user_id"], year)[0]
        if result:
            total_incomes[month] = result['total_incomes'] or 0
            total_expenses[month] = result['total_expenses'] or 0
            total_savings[month] = result['total_savings'] or 0
        else:
            total_incomes[month] = 0
            total_expenses[month] = 0
            total_savings[month] = 0


    return render_template("planning.html", category_list=category_list, plannings=plannings, total_incomes=total_incomes, total_expenses=total_expenses, total_savings=total_savings, selected_year=selected_year)

# --------------------------------------------------------- REGISTRATION & LOGIN -----------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("update.html", error="invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")

    if request.method == "POST":
        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        elif not confirmation:
            return apology("must re-type the password", 400)

        if password != confirmation:
            return render_template("register.html", error="Incorrect match")

        check_exist = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(check_exist) != 0:
            return render_template("register.html", error="Username already existed")

        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username,
            hashed_password,
        )

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]

        # Add Default Category
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Income", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Housing", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Utilities", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Transportation", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Insurance", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Entertainment", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Education", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Clothing", "add_category", session['user_id'])
        db.execute("INSERT INTO categories (name, types, user_id) VALUES (?, ?, ?)", "Miscellaneous", "add_category", session['user_id'])



        return redirect("/")
    else:
        return render_template("register.html")
