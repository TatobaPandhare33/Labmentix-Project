-- sql_scripts.sql
-- SQL schema for video game analytics (suggested)
-- Run this in SQLite or adapt for other DBs

-- 1) games table (engagement data)
CREATE TABLE IF NOT EXISTS games (
  game_id INTEGER PRIMARY KEY AUTOINCREMENT,
  Title TEXT,
  Rating REAL,
  Genres TEXT,
  Plays REAL,
  Backlogs REAL,
  Wishlist REAL,
  Release_Date TEXT,
  Release_Year INTEGER,
  Platform TEXT,
  Team TEXT
);

-- 2) sales table (regional sales)
CREATE TABLE IF NOT EXISTS sales (
  sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT,
  Platform TEXT,
  Year INTEGER,
  Genre TEXT,
  Publisher TEXT,
  NA_Sales REAL,
  EU_Sales REAL,
  JP_Sales REAL,
  Other_Sales REAL,
  Global_Sales REAL
);

-- 3) merged table (join of games + sales)
CREATE TABLE IF NOT EXISTS merged (
  merged_id INTEGER PRIMARY KEY AUTOINCREMENT,
  Title TEXT,
  Rating REAL,
  Genres TEXT,
  Plays REAL,
  Wishlist REAL,
  Release_Year INTEGER,
  Platform TEXT,
  Team TEXT,
  Publisher TEXT,
  NA_Sales REAL,
  EU_Sales REAL,
  JP_Sales REAL,
  Other_Sales REAL,
  Global_Sales REAL
);

-- Example queries:

-- Top 10 Global Sellers
SELECT Name AS Title, Global_Sales
FROM sales
ORDER BY Global_Sales DESC
LIMIT 10;

-- Top Genres by Global Sales (using merged)
SELECT Genres, SUM(Global_Sales) AS Total_Global_Sales
FROM merged
GROUP BY Genres
ORDER BY Total_Global_Sales DESC
LIMIT 10;

-- Average Rating by Genre
SELECT Genres, ROUND(AVG(Rating),2) AS Avg_Rating
FROM merged
GROUP BY Genres
ORDER BY Avg_Rating DESC
LIMIT 10;

-- Publisher performance
SELECT Publisher, SUM(Global_Sales) AS Total_Sales, COUNT(DISTINCT Title) AS Titles
FROM merged
GROUP BY Publisher
ORDER BY Total_Sales DESC
LIMIT 20;
