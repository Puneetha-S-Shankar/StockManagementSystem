CREATE DATABASE StockManagement1;
USE StockManagement1;

CREATE TABLE Users (
    user_id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(15),
    city VARCHAR(50),
    created_at VARCHAR(20) 
);

CREATE TABLE Stocks (
    stock_id INT PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE,
    company_name VARCHAR(255),
    sector VARCHAR(50),
    current_price DECIMAL(10,2)
);

CREATE TABLE Brokers (
    broker_id INT PRIMARY KEY,
    name VARCHAR(100),
    commission_rate DECIMAL(5,2),
    contact_email VARCHAR(100) UNIQUE
);

CREATE TABLE Transactions (
    transaction_id INT PRIMARY KEY,
    user_id INT,
    stock_id INT,
    broker_id INT,
    transaction_type VARCHAR(10),
    quantity INT,
    price DECIMAL(10,2),
    transaction_date VARCHAR(20), 
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE,
    FOREIGN KEY (broker_id) REFERENCES Brokers(broker_id) ON DELETE SET NULL
);

CREATE TABLE Portfolio_Holdings (
    holding_id INT PRIMARY KEY,
    user_id INT,
    stock_id INT,
    quantity INT,
    purchase_date VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);

CREATE TABLE Dividends (
    dividend_id INT PRIMARY KEY,
    stock_id INT,
    amount DECIMAL(10,2),
    payment_date VARCHAR(20),
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);

CREATE TABLE Stock_Prices (
    price_id INT PRIMARY KEY,
    stock_id INT,
    price DECIMAL(10,2),
    recorded_at VARCHAR(20), 
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);

CREATE TABLE Watchlist (
    watchlist_id INT PRIMARY KEY,
    user_id INT,
    stock_id INT,
    added_on VARCHAR(20), 
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);

CREATE TABLE Orders (
    order_id INT PRIMARY KEY,
    user_id INT,
    stock_id INT,
    quantity INT,
    order_status VARCHAR(20),
    order_date VARCHAR(20), 
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);

CREATE TABLE Logs (
    log_id INT PRIMARY KEY,
    action VARCHAR(255),
    performed_by VARCHAR(100),
    log_timestamp VARCHAR(20) 
);
ALTER TABLE Users MODIFY user_id INT NOT NULL AUTO_INCREMENT;

-- Drop all foreign key constraints first
ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_1;

ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_2;
ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_3;

ALTER TABLE Portfolio_Holdings DROP FOREIGN KEY portfolio_holdings_ibfk_1;
ALTER TABLE Portfolio_Holdings DROP FOREIGN KEY portfolio_holdings_ibfk_2;
ALTER TABLE Dividends DROP FOREIGN KEY dividends_ibfk_1;
ALTER TABLE Stock_Prices DROP FOREIGN KEY stock_prices_ibfk_1;
ALTER TABLE Watchlist DROP FOREIGN KEY watchlist_ibfk_1;
ALTER TABLE Watchlist DROP FOREIGN KEY watchlist_ibfk_2;
ALTER TABLE Orders DROP FOREIGN KEY orders_ibfk_1;
ALTER TABLE Orders DROP FOREIGN KEY orders_ibfk_2;

-- Modify all primary key columns to auto increment
ALTER TABLE Users MODIFY user_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Stocks MODIFY stock_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Brokers MODIFY broker_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Transactions MODIFY transaction_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Portfolio_Holdings MODIFY holding_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Dividends MODIFY dividend_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Stock_Prices MODIFY price_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Watchlist MODIFY watchlist_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Orders MODIFY order_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Logs MODIFY log_id INT NOT NULL AUTO_INCREMENT;

-- Recreate all foreign key constraints
ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_3 FOREIGN KEY (broker_id) REFERENCES Brokers(broker_id) ON DELETE SET NULL;
ALTER TABLE Portfolio_Holdings ADD CONSTRAINT portfolio_holdings_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Portfolio_Holdings ADD CONSTRAINT portfolio_holdings_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Dividends ADD CONSTRAINT dividends_ibfk_1 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Stock_Prices ADD CONSTRAINT stock_prices_ibfk_1 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Watchlist ADD CONSTRAINT watchlist_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Watchlist ADD CONSTRAINT watchlist_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Orders ADD CONSTRAINT orders_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Orders ADD CONSTRAINT orders_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;



SHOW CREATE TABLE Orders;
ALTER TABLE Orders MODIFY order_id INT NOT NULL AUTO_INCREMENT;
DROP TABLE Orders;

CREATE TABLE Orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    stock_id INT,
    quantity INT,
    order_status VARCHAR(20),
    order_date VARCHAR(20), 
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE
);
ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_1;
ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_2;
ALTER TABLE Transactions DROP FOREIGN KEY transactions_ibfk_3;
ALTER TABLE Portfolio_Holdings DROP FOREIGN KEY portfolio_holdings_ibfk_1;
ALTER TABLE Portfolio_Holdings DROP FOREIGN KEY portfolio_holdings_ibfk_2;
ALTER TABLE Dividends DROP FOREIGN KEY dividends_ibfk_1;
ALTER TABLE Stock_Prices DROP FOREIGN KEY stock_prices_ibfk_1;
ALTER TABLE Watchlist DROP FOREIGN KEY watchlist_ibfk_1;
ALTER TABLE Watchlist DROP FOREIGN KEY watchlist_ibfk_2;
ALTER TABLE Orders DROP FOREIGN KEY orders_ibfk_1;
ALTER TABLE Orders DROP FOREIGN KEY orders_ibfk_2;

ALTER TABLE Users MODIFY user_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Stocks MODIFY stock_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Brokers MODIFY broker_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Transactions MODIFY transaction_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Portfolio_Holdings MODIFY holding_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Dividends MODIFY dividend_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Stock_Prices MODIFY price_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Watchlist MODIFY watchlist_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Orders MODIFY order_id INT NOT NULL AUTO_INCREMENT;
ALTER TABLE Logs MODIFY log_id INT NOT NULL AUTO_INCREMENT;

ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Transactions ADD CONSTRAINT transactions_ibfk_3 FOREIGN KEY (broker_id) REFERENCES Brokers(broker_id) ON DELETE SET NULL;
ALTER TABLE Portfolio_Holdings ADD CONSTRAINT portfolio_holdings_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Portfolio_Holdings ADD CONSTRAINT portfolio_holdings_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Dividends ADD CONSTRAINT dividends_ibfk_1 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Stock_Prices ADD CONSTRAINT stock_prices_ibfk_1 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Watchlist ADD CONSTRAINT watchlist_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Watchlist ADD CONSTRAINT watchlist_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
ALTER TABLE Orders ADD CONSTRAINT orders_ibfk_1 FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
ALTER TABLE Orders ADD CONSTRAINT orders_ibfk_2 FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id) ON DELETE CASCADE;
USE StockManagement1;
SELECT * FROM Users;















