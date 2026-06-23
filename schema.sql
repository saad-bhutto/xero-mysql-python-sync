CREATE TABLE `invoices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` VARCHAR(190) DEFAULT NULL,
  `type` varchar(10) DEFAULT NULL,
  `contact_id` VARCHAR(190) DEFAULT NULL,
  `contact_name` varchar(255) DEFAULT NULL,
  `DATE` datetime DEFAULT NULL,
  `line_amount_types` varchar(50) DEFAULT NULL,
  `invoice_number` varchar(50) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `branding_theme_id` VARCHAR(190) DEFAULT NULL,
  `currency_code` char(3) DEFAULT NULL,
  `currency_rate` decimal(10,4) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL,
  `total_tax` decimal(10,2) DEFAULT NULL,
  `total` decimal(10,2) DEFAULT NULL,
  `has_attachments` tinyint(1) DEFAULT NULL,
  `is_discounted` tinyint(1) DEFAULT NULL,
  `amount_due` decimal(10,2) DEFAULT NULL,
  `amount_paid` decimal(10,2) DEFAULT NULL,
  `amount_credited` decimal(10,2) DEFAULT NULL,
  `updated_date_utc` datetime DEFAULT NULL,
  `has_errors` tinyint(1) DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `invoice_id` (`invoice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `line_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `line_item_id` VARCHAR(190) DEFAULT NULL,
  `invoice_id` VARCHAR(190) DEFAULT NULL,
  `description` text,
  `quantity` decimal(10,2) DEFAULT NULL,
  `unit_amount` decimal(10,2) DEFAULT NULL,
  `item_code` varchar(50) DEFAULT NULL,
  `account_code` varchar(50) DEFAULT NULL,
  `account_id` VARCHAR(190) DEFAULT NULL,
  `tax_type` varchar(50) DEFAULT NULL,
  `tax_amount` decimal(10,2) DEFAULT NULL,
  `line_amount` decimal(10,2) DEFAULT NULL,
  `item_id` VARCHAR(190) DEFAULT NULL,
  `item_name` varchar(255) DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `line_item_id` (`line_item_id`),
  KEY `invoice_id` (`invoice_id`),
  CONSTRAINT `line_items_ibfk_1` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`invoice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `xero_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(128) NOT NULL,
  `tenant_id` varchar(128) NOT NULL,
  `access_token` text,
  `refresh_token` text,
  `expires_in` int DEFAULT NULL,
  `expires_at` double DEFAULT NULL,
  `token_type` varchar(32) DEFAULT NULL,
  `scope` text,
  `id_token` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_tenant` (`user_id`,`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE purchase_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id VARCHAR(190) UNIQUE,
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    delivery_date DATETIME,
    line_amount_types VARCHAR(50),
    purchase_order_number VARCHAR(50),
    reference VARCHAR(255),
    branding_theme_id VARCHAR(190),
    currency_code CHAR(3),
    currency_rate DECIMAL(10, 4),
    status VARCHAR(50),
    subtotal DECIMAL(10, 2),
    total_tax DECIMAL(10, 2),
    total DECIMAL(10, 2),
    has_attachments BOOLEAN,
    is_discounted BOOLEAN,
    amount_due DECIMAL(10, 2),
    amount_paid DECIMAL(10, 2),
    amount_credited DECIMAL(10, 2),
    updated_date_utc DATETIME,
    has_errors BOOLEAN,
    delivery_address TEXT,
    attention_to VARCHAR(255),
    expected_arrival_date DATETIME
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;



CREATE TABLE purchase_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    purchase_order_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10, 2),
    unit_amount DECIMAL(10, 2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10, 2),
    line_amount DECIMAL(10, 2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(purchase_order_id)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE credit_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credit_note_id VARCHAR(190) UNIQUE,
    type VARCHAR(10), -- Usually 'ACCPAYCREDIT' or 'ACCRECCREDIT'
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    line_amount_types VARCHAR(50),
    credit_note_number VARCHAR(50),
    reference VARCHAR(255),
    branding_theme_id VARCHAR(190),
    currency_code CHAR(3),
    currency_rate DECIMAL(10, 4),
    status VARCHAR(50),
    subtotal DECIMAL(10, 2),
    total_tax DECIMAL(10, 2),
    total DECIMAL(10, 2),
    has_attachments BOOLEAN,
    is_discounted BOOLEAN,
    amount_due DECIMAL(10, 2),
    amount_paid DECIMAL(10, 2),
    amount_credited DECIMAL(10, 2),
    updated_date_utc DATETIME,
    has_errors BOOLEAN
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE credit_note_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    credit_note_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10, 2),
    unit_amount DECIMAL(10, 2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10, 2),
    line_amount DECIMAL(10, 2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    FOREIGN KEY (credit_note_id) REFERENCES credit_notes(credit_note_id)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE quotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_id VARCHAR(190) UNIQUE,
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    quote_number VARCHAR(50),
    reference VARCHAR(255),
    status VARCHAR(50),
    title VARCHAR(255),
    summary TEXT,
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    date DATETIME,
    expiry_date DATETIME,
    line_amount_types VARCHAR(50),
    subtotal DECIMAL(10,2),
    total_tax DECIMAL(10,2),
    total DECIMAL(10,2),
    updated_date_utc DATETIME,
    has_attachments BOOLEAN,
    has_errors BOOLEAN
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE quote_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    quote_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10,2),
    unit_amount DECIMAL(10,2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10,2),
    line_amount DECIMAL(10,2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;



CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    payment_id VARCHAR(190) UNIQUE,
    invoice_id VARCHAR(190),
    credit_note_id VARCHAR(190),
    prepayment_id VARCHAR(190),
    overpayment_id VARCHAR(190),
    account_id VARCHAR(190),
    account_code VARCHAR(50),
    reference VARCHAR(255),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    date DATETIME,
    amount DECIMAL(10,2),
    status VARCHAR(50),
    type VARCHAR(50),
    updated_date_utc DATETIME
    -- Depending on the Xero API object, some fields may be null (e.g., if the payment is not tied to an invoice)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;



CREATE TABLE payment_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    payment_id VARCHAR(190),
    applied_to_id VARCHAR(190), -- invoice_id, credit_note_id, etc.
    applied_to_type VARCHAR(50), -- e.g., 'Invoice', 'CreditNote'
    amount DECIMAL(10,2),
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bank Transactions
CREATE TABLE bank_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bank_transaction_id VARCHAR(190) UNIQUE,
    type VARCHAR(50),
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    line_amount_types VARCHAR(50),
    reference VARCHAR(255),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    status VARCHAR(50),
    subtotal DECIMAL(10,2),
    total_tax DECIMAL(10,2),
    total DECIMAL(10,2),
    updated_date_utc DATETIME,
    has_attachments BOOLEAN,
    amount_paid DECIMAL(10,2),
    amount_due DECIMAL(10,2),
    amount_credited DECIMAL(10,2),
    has_errors BOOLEAN,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE bank_transaction_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    bank_transaction_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10,2),
    unit_amount DECIMAL(10,2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10,2),
    line_amount DECIMAL(10,2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    deleted_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (bank_transaction_id) REFERENCES bank_transactions(bank_transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bank Transfers
CREATE TABLE bank_transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bank_transfer_id VARCHAR(190) UNIQUE,
    from_bank_account_id VARCHAR(190),
    to_bank_account_id VARCHAR(190),
    amount DECIMAL(10,2),
    date DATETIME,
    reference VARCHAR(255),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    status VARCHAR(50),
    updated_date_utc DATETIME,
    has_attachments BOOLEAN,
    has_errors BOOLEAN,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Linked Transactions
CREATE TABLE linked_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    linked_transaction_id VARCHAR(190) UNIQUE,
    source_transaction_id VARCHAR(190),
    source_line_item_id VARCHAR(190),
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    status VARCHAR(50),
    type VARCHAR(50),
    description TEXT,
    updated_date_utc DATETIME,
    amount DECIMAL(10,2),
    has_errors BOOLEAN,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Expense Claims
CREATE TABLE expense_claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_claim_id VARCHAR(190) UNIQUE,
    user_id VARCHAR(190),
    user_name VARCHAR(255),
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    expense_claim_number VARCHAR(50),
    reference VARCHAR(255),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    status VARCHAR(50),
    subtotal DECIMAL(10,2),
    total_tax DECIMAL(10,2),
    total DECIMAL(10,2),
    has_attachments BOOLEAN,
    amount_due DECIMAL(10,2),
    amount_paid DECIMAL(10,2),
    amount_credited DECIMAL(10,2),
    updated_date_utc DATETIME,
    has_errors BOOLEAN,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE expense_claim_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    expense_claim_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10,2),
    unit_amount DECIMAL(10,2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10,2),
    line_amount DECIMAL(10,2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    deleted_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (expense_claim_id) REFERENCES expense_claims(expense_claim_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Receipts
CREATE TABLE receipts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receipt_id VARCHAR(190) UNIQUE,
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    line_amount_types VARCHAR(50),
    reference VARCHAR(255),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    status VARCHAR(50),
    subtotal DECIMAL(10,2),
    total_tax DECIMAL(10,2),
    total DECIMAL(10,2),
    has_attachments BOOLEAN,
    amount_due DECIMAL(10,2),
    amount_paid DECIMAL(10,2),
    amount_credited DECIMAL(10,2),
    updated_date_utc DATETIME,
    has_errors BOOLEAN,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE receipt_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    receipt_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10,2),
    unit_amount DECIMAL(10,2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10,2),
    line_amount DECIMAL(10,2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    deleted_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Repeating Invoices
CREATE TABLE repeating_invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    repeating_invoice_id VARCHAR(190) UNIQUE,
    contact_id VARCHAR(190),
    contact_name VARCHAR(255),
    date DATETIME,
    line_amount_types VARCHAR(50),
    reference VARCHAR(255),
    branding_theme_id VARCHAR(190),
    currency_code CHAR(3),
    currency_rate DECIMAL(10,4),
    status VARCHAR(50),
    subtotal DECIMAL(10,2),
    total_tax DECIMAL(10,2),
    total DECIMAL(10,2),
    has_attachments BOOLEAN,
    is_discounted BOOLEAN,
    amount_due DECIMAL(10,2),
    amount_paid DECIMAL(10,2),
    amount_credited DECIMAL(10,2),
    updated_date_utc DATETIME,
    has_errors BOOLEAN,
    schedule_type VARCHAR(50),
    schedule_every VARCHAR(50),
    schedule_start_date DATETIME,
    schedule_end_date DATETIME,
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE repeating_invoice_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    line_item_id VARCHAR(190) UNIQUE,
    repeating_invoice_id VARCHAR(190),
    description TEXT,
    quantity DECIMAL(10,2),
    unit_amount DECIMAL(10,2),
    item_code VARCHAR(50),
    account_code VARCHAR(50),
    account_id VARCHAR(190),
    tax_type VARCHAR(50),
    tax_amount DECIMAL(10,2),
    line_amount DECIMAL(10,2),
    item_id VARCHAR(190),
    item_name VARCHAR(255),
    deleted_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (repeating_invoice_id) REFERENCES repeating_invoices(repeating_invoice_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
