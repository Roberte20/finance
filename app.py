
import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    user=db.execute("SELECT * FROM users WHERE id=:userid", userid=session["user_id"])
    balance=usd(user[0]["cash"])
    print(user)
    userstocks=db.execute("SELECT symbol, shares FROM stocks WHERE user_id=:userid",userid=session["user_id"])
    
    print(userstocks)
    for stock in userstocks:
        symbol=stock["symbol"]
        shares=stock["shares"]
        info=lookup(stock["symbol"])
        price=info["price"]
        name=info["name"]
        stock.update({"price":usd(price)})
        stock.update({"name":name})
        stock.update({"total":usd(price*shares)})

    """Show portfolio of stocks"""
    return render_template('index.html', balance=balance, userstocks=userstocks)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    if request.method == "POST":
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("Please provide a symbol and/or share numbers!", 403)
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("Symbol does not exist")
        symbol= lookup(request.form.get("symbol"))
        print(symbol)
        shareprice=symbol["price"]
        usercash= db.execute("SELECT cash FROM users WHERE id= :userid", userid=session["user_id"])
        print(usercash)
        print(shareprice)
        print(symbol)
        finalcost=shareprice*int(request.form.get("shares"))
        updatedcost=float(usercash[0]['cash'])-finalcost
        print(updatedcost)
        if float(usercash[0]['cash']) < shareprice * int(request.form.get("shares")):
            return apology("You do not have enough money!", 403)
        
        db.execute("UPDATE users SET cash = :updatedcost WHERE id=:userid",updatedcost=updatedcost, userid=session["user_id"])
        
        check_stock=db.execute("SELECT shares FROM stocks WHERE symbol=:symbolcheck",symbolcheck=request.form.get("symbol")) 
        stockref=int(request.form.get("shares"))
        print(check_stock)
        
        if len(check_stock)==1:
            finalcheck=check_stock[0]["shares"] + stockref
            db.execute("UPDATE stocks SET shares = :finalcheck WHERE symbol=:symbol", finalcheck=finalcheck, symbol=request.form.get("symbol"))
        else:
             db.execute("INSERT INTO stocks(user_id,symbol,shares) VALUES(:user_id,:symbol,:shares)", user_id=session["user_id"],symbol=symbol['symbol'],shares=int(request.form.get("shares")))
        
        return redirect("/")
         
   


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method =="POST":
        rows=lookup(request.form.get("symbol"))
        if not rows:
            return apology("The symbol does not exist in our database")
        return render_template("quoted.html",stock = rows)
    else:
        return render_template("quote.html")
    """Get stock quote."""


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("confirmation"):
            return apology("must confirm password",403)
        elif (request.form.get("password") != request.form.get("confirmation")):
            return apology("Your passwords do not match", 403)
        rows= db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if (len(rows) != 0):
            return apology("Username already taken", 403)
        else:
#             password = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username,hash) VALUES(:username, :password)", username = request.form.get("username"), password=generate_password_hash(request.form.get("password")))
        return apology("You are registered!", 403)
    else:
        return render_template("register.html")

    """Register user"""
    


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html")
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("Symbol does not exist")
        soldshares= request.form.get("shares")
        if not soldshares:
            return apology("Please enter a number of shares")
        finalshares=int(soldshares)
        ownedshares=db.execute("SELECT shares FROM stocks WHERE user_id=:user_id and symbol=:symbol",user_id=session["user_id"],symbol=symbol["symbol"])
        if not ownedshares or ownedshares[0]["shares"]<finalshares:
            return apology("You do not have enough shares to sell!")
        sharecost=finalshares * symbol["price"]
        total= db.execute("SELECT cash FROM users where id=:id", id=session["user_id"])
        finaltotal=sharecost + total[0]["cash"]
        db.execute("UPDATE users SET cash =:finaltotal WHERE id =:id",id=session["user_id"], finaltotal=finaltotal)
        newshares=ownedshares[0]["shares"]-finalshares
        if newshares==0:
            db.execute("DELETE FROM stocks WHERE user_id=:user_id AND symbol=:symbol", user_id=session["user_id"],symbol=symbol["symbol"])
        else:
            db.execute("UPDATE stocks SET shares=:shares WHERE user_id=:user_id AND symbol=:symbol", shares=newshares, user_id=session["user_id"], symbol=symbol["symbol"])
        return redirect("/")
         


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
