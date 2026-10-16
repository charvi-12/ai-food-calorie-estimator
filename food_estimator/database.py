import sqlite3
from datetime import date, timedelta

from flask import current_app, g

from .nutrition import FOODS


def connect_database(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db():
    if "db" not in g:
        g.db = connect_database(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialize_database(database_path):
    with connect_database(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS foods (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                carbohydrates REAL NOT NULL,
                fat REAL NOT NULL,
                source TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_id TEXT NOT NULL REFERENCES foods(id),
                serving_grams REAL NOT NULL CHECK(serving_grams > 0),
                meal_type TEXT NOT NULL,
                eaten_on TEXT NOT NULL,
                image_filename TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS meals_eaten_on_idx ON meals(eaten_on);
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO foods
                (id, name, category, calories, protein, carbohydrates, fat, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            FOODS,
        )


def get_foods(connection=None):
    connection = connection or get_db()
    return connection.execute(
        "SELECT id, name, category, calories, protein, carbohydrates, fat, source "
        "FROM foods ORDER BY CASE category WHEN 'Indian' THEN 0 ELSE 1 END, name"
    ).fetchall()


def get_food(food_id, connection=None):
    connection = connection or get_db()
    return connection.execute(
        "SELECT id, name, category, calories, protein, carbohydrates, fat, source "
        "FROM foods WHERE id = ?",
        (food_id,),
    ).fetchone()


def get_meal_rows(connection, eaten_on):
    return connection.execute(
        """
        SELECT meals.id, meals.food_id, foods.name, foods.category, foods.calories, foods.protein,
               foods.carbohydrates, foods.fat, meals.serving_grams, meals.meal_type,
               meals.eaten_on, meals.image_filename, meals.created_at
        FROM meals JOIN foods ON foods.id = meals.food_id
        WHERE meals.eaten_on = ?
        ORDER BY meals.created_at DESC, meals.id DESC
        """,
        (eaten_on,),
    ).fetchall()


def summarize_meals(meals):
    totals = {"calories": 0.0, "protein": 0.0, "carbohydrates": 0.0, "fat": 0.0}
    for meal in meals:
        multiplier = meal["serving_grams"] / 100
        for nutrient in totals:
            totals[nutrient] += meal[nutrient] * multiplier
    return {nutrient: round(amount, 1) for nutrient, amount in totals.items()}


def get_weekly_calories(connection, end_date=None):
    end_date = end_date or date.today()
    first_date = end_date - timedelta(days=6)
    rows = connection.execute(
        """
        SELECT meals.eaten_on, SUM(foods.calories * meals.serving_grams / 100) AS calories
        FROM meals JOIN foods ON foods.id = meals.food_id
        WHERE meals.eaten_on BETWEEN ? AND ?
        GROUP BY meals.eaten_on
        """,
        (first_date.isoformat(), end_date.isoformat()),
    ).fetchall()
    by_day = {row["eaten_on"]: round(row["calories"], 1) for row in rows}
    days = [first_date + timedelta(days=offset) for offset in range(7)]
    return {
        "today": end_date.isoformat(),
        "labels": [day.strftime("%a") for day in days],
        "dates": [day.isoformat() for day in days],
        "calories": [by_day.get(day.isoformat(), 0) for day in days],
    }


def register_database(app):
    app.teardown_appcontext(close_db)
