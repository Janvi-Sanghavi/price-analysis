SET GLOBAL local_infile = 1;
CREATE DATABASE mandi_db;
USE mandi_db;
CREATE TABLE staging_prices(
	arrival_data DATE,
	state VARCHAR(50),
    district VARCHAR(50),
    market VARCHAR(100),
    commodity VARCHAR(20),
    variety VARCHAR(50),
    grade VARCHAR(30),
    min_price DECIMAL(12, 2),
    max_price DECIMAL(12, 2),
    modal_price DECIMAL(12, 2)
);
LOAD DATA LOCAL INFILE 'C:/Projects/india-vegetable-price-analysis/sql/mandi_prices_clean.csv'
INTO TABLE staging_prices
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
CREATE TABLE districts (
	district_id INT AUTO_INCREMENT PRIMARY KEY,
    district_name VARCHAR(50) NOT NULL UNIQUE,
    state VARCHAR(50),
    region VARCHAR(20),
    city_type VARCHAR(20)
);

INSERT INTO districts (district_name, state, region, city_type) VALUES
('Nashik', 'Maharashtra', 'West', 'Producer'),
('Pune', 'Maharashtra', 'West', 'Producer'),
('Delhi', 'NCT of Delhi', 'North', 'Consumer'),
('Bengaluru', 'Karnataka', 'South', 'Consumer');

CREATE TABLE commodities (
	commodity_id INT AUTO_INCREMENT PRIMARY KEY,
    commodity_name VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO commodities (commodity_name)
SELECT DISTINCT commodity FROM staging_prices;

SELECT * FROM districts;
SELECT * FROM commodities;

CREATE TABLE markets (
	market_id INT AUTO_INCREMENT PRIMARY KEY,
    market_name VARCHAR(100) NOT NULL,
    district_id INT NOT NULL,
    FOREIGN KEY (district_id) REFERENCES districts(district_id)
);

INSERT INTO markets (market_name, district_id)
SELECT DISTINCT s.market, d.district_id
FROM staging_prices s
JOIN districts d ON s.district = d.district_name;

SELECT COUNT(*) FROM markets;

CREATE TABLE prices (
	price_id INT AUTO_INCREMENT PRIMARY KEY,
    arrival_date DATE NOT NULL,
    market_id INT NOT NULL,
    commodity_id INT NOT NULL,
    variety VARCHAR(50),
    grade VARCHAR(50),
    min_price DECIMAL(12, 2),
    max_price DECIMAL(12, 2),
    modal_price DECIMAL(12, 2),
    FOREIGN KEY (market_id) REFERENCES markets(market_id),
    FOREIGN KEY (commodity_id) REFERENCES commodities(commodity_id)
);

ALTER TABLE staging_prices RENAME COLUMN arrival_data to arrival_date;
DESCRIBE staging_prices;

TRUNCATE TABLE prices;

INSERT INTO prices (arrival_date, market_id, commodity_id, variety, grade, min_price, max_price, modal_price)
SELECT s.arrival_date, m.market_id, c.commodity_id, s.variety, s.grade, s.min_price, s.max_price, s.modal_price
FROM staging_prices s
JOIN districts d ON s.district = d.district_name
JOIN markets m ON s.market = m.market_name AND m.district_id = d.district_id
JOIN commodities c ON s.commodity = c.commodity_name;

SELECT COUNT(*) FROM prices;

-- Q1: Average prices per kg by commodity
SELECT c.commodity_name, ROUND(AVG(p.modal_price) / 100, 1) AS avg_price_per_kg, COUNT(*) AS records
FROM prices p
JOIN commodities c ON p.commodity_id = c.commodity_id
GROUP BY c.commodity_name
ORDER BY avg_price_per_kg DESC;

-- Q2: Average price by city and commodity(2022-2025)
SELECT d.district_name, c.commodity_name, ROUND(AVG(p.modal_price) / 100, 1) AS avg_price_per_kg
FROM prices p
JOIN commodities c ON p.commodity_id = c.commodity_id
JOIN markets m ON p.market_id = m.market_id
JOIN districts d ON m.district_id = d.district_id
WHERE YEAR(p.arrival_date) BETWEEN 2022 AND 2025
GROUP BY d.district_name, c.commodity_name
ORDER BY c.commodity_name, avg_price_per_kg DESC;

-- Q3: Markets with more than 5,000 price records
SELECT m.market_name, COUNT(*) AS records
FROM prices p
JOIN markets m ON p.market_id = m.market_id
GROUP BY m.market_name
HAVING COUNT(*) > 5000
ORDER BY records DESC;

-- Q4: Rank cities by average price within each commodity(2022- 2025)
WITH city_prices AS (
	SELECT c.commodity_name, d.district_name, ROUND(AVG(p.modal_price) / 100, 1) AS avg_price
    FROM prices p
    JOIN commodities c ON p.commodity_id = c.commodity_id
    JOIN markets m ON p.market_id = m.market_id
    JOIN districts d ON m.district_id = d.district_id
    WHERE YEAR(p.arrival_date) BETWEEN 2022 AND 2025
    GROUP BY c.commodity_name, d.district_name
)
SELECT commodity_name, district_name, avg_price, RANK() OVER (PARTITION BY commodity_name ORDER BY avg_price DESC) AS price_rank
FROM city_prices;

-- Q5: Month-on-month change in tomato price (2023)
WITH monthly AS (
	SELECT MONTH(p.arrival_date) AS month_no, ROUND(AVG(p.modal_price) /100, 1) AS avg_price
    FROM prices p
    JOIN commodities c ON p.commodity_id = c.commodity_id
    WHERE c.commodity_name = 'Tomato' AND YEAR(p.arrival_date) = 2023
    GROUP BY MONTH(p.arrival_date)
)
SELECT month_no, avg_price, LAG(avg_price) OVER (ORDER BY month_no) AS prev_month_price, ROUND(avg_price - LAG(avg_price) OVER (ORDER BY month_no), 1) AS change_rs
FROM monthly;

-- Q6: Most expensive month for each commodity (2022- 2026)
WITH monthly AS (
	SELECT c.commodity_name, MONTH(p.arrival_date) AS month_no, ROUND(AVG(p.modal_price) / 100, 1) AS avg_price
    FROM prices p
    JOIN commodities c ON p.commodity_id = c.commodity_id
    WHERE YEAR(p.arrival_date) >= 2022
    GROUP BY c.commodity_name, MONTH(p.arrival_date)
),
ranked AS (
	SELECT *, RANK() OVER (PARTITION BY commodity_name ORDER BY avg_price DESC) AS rnk 
	FROM monthly
)
SELECT commodity_name, month_no, avg_price
FROM ranked
WHERE rnk = 1;
