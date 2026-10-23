-- Synthetic fixture generated from main ba3aba3f932753de1dc9014c52558768b84f0b38. No live data or credentials.
BEGIN TRANSACTION;
CREATE TABLE app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO "app_settings" VALUES('assignment_template_minutes','10080,4320,1440,180');
INSERT INTO "app_settings" VALUES('exam_template_minutes','10080,4320,1440,120,30');
INSERT INTO "app_settings" VALUES('lab_template_minutes','10080,4320,1440,180');
INSERT INTO "app_settings" VALUES('expense_template_minutes','4320,1440,180');
INSERT INTO "app_settings" VALUES('expense_dayof_local_time','09:00');
INSERT INTO "app_settings" VALUES('quiet_start','23:00');
INSERT INTO "app_settings" VALUES('quiet_end','07:00');
INSERT INTO "app_settings" VALUES('todo_reminder_enabled','off');
INSERT INTO "app_settings" VALUES('todo_reminder_minutes','60');
INSERT INTO "app_settings" VALUES('todo_reminder_last_sent_utc','');
CREATE TABLE auth_audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_id INTEGER,
          target_id INTEGER,
          action TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(actor_id) REFERENCES users(id),
          FOREIGN KEY(target_id) REFERENCES users(id)
        );
CREATE TABLE auth_email_tokens (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          purpose TEXT NOT NULL CHECK(purpose IN ('verify_email','password_reset')),
          token_hash TEXT NOT NULL UNIQUE,
          candidate_email TEXT,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          used_at TEXT
        );
CREATE TABLE class_meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
  start_time_local TEXT NOT NULL, -- "HH:MM"
  duration_minutes INTEGER NOT NULL DEFAULT 50,
  location TEXT,
  remind_before_minutes INTEGER NOT NULL DEFAULT 15,
  notes TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  term TEXT,
  color TEXT,
  created_at_utc TEXT NOT NULL
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'meeting',
  location TEXT,
  start_at_utc TEXT NOT NULL,
  end_at_utc TEXT,
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  category TEXT,
  amount REAL NOT NULL,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unpaid' CHECK(status IN ('unpaid','paid')),
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  recurrence TEXT NOT NULL DEFAULT 'none',
  recurrence_interval INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE finance_budget_rows(
            section TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'Monthly',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(section, name)
        );
INSERT INTO "finance_budget_rows" VALUES('income','Employment income',0.0,'Annually','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('income','Household members'' employment income',0.0,'Annually','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('income','Rental income',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('income','Pension income',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('income','Benefits and support payments',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Mortgage or rent',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Property tax',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Electricity, gas and water',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Homeowner or renter''s insurance',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Condo fees',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Home security service',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Maintenance costs',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Internet, cable and home phone',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Mobile phone',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Streaming media subscriptions',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Other digital subscriptions',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Groceries',123.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Meal kits and food-delivery services',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Cafés and coffee shops',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Restaurants (dine-in, delivery or takeout)',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Personal loan payments',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Credit card or line of credit interest',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Student loan payments',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Car loan or lease payments',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Gas and electric vehicle charging',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Repairs and maintenance',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Insurance and registration',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Parking and tolls',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Public transit',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Ride-share and taxis',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Car- or bike-share membership',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Children''s clothes',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Childcare',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Children''s recreation',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Tuition and tutoring',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Eldercare and other dependants',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Pet care',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Dry-cleaning and laundry',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Insurance premiums',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Prescription drugs',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Dental and eye care',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Hair, spa and beauty services',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Fitness, sports and club memberships',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Mental health and wellbeing',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Clothing and accessories',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Housewares and decor',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Personal care products',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Tickets for events and attractions',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Hobbies and recreation',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Gifts',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Charitable donations',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Professional fees',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('expenses','Other',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Emergency fund',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Retirement',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Home purchase or renovations',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Vacations',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Major purchases',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Education',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_budget_rows" VALUES('savings','Future family expenses',0.0,'Monthly','2026-10-23T14:56:09.010142+00:00','2026-10-23T14:56:09.010142+00:00');
CREATE TABLE finance_categories(
            name TEXT PRIMARY KEY,
            is_custom INTEGER NOT NULL DEFAULT 0,
            created_at_utc TEXT NOT NULL
        );
INSERT INTO "finance_categories" VALUES('Mortgage or rent',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Property tax',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Electricity, gas and water',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Homeowner or renter''s insurance',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Condo fees',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Home security service',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Maintenance costs',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Internet, cable and home phone',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Mobile phone',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Streaming media subscriptions',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Other digital subscriptions',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Groceries',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Meal kits and food-delivery services',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Cafés and coffee shops',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Restaurants (dine-in, delivery or takeout)',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Personal loan payments',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Credit card or line of credit interest',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Student loan payments',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Car loan or lease payments',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Gas and electric vehicle charging',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Repairs and maintenance',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Insurance and registration',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Parking and tolls',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Public transit',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Ride-share and taxis',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Car- or bike-share membership',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Children''s clothes',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Childcare',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Children''s recreation',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Tuition and tutoring',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Eldercare and other dependants',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Pet care',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Dry-cleaning and laundry',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Insurance premiums',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Prescription drugs',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Dental and eye care',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Hair, spa and beauty services',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Fitness, sports and club memberships',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Mental health and wellbeing',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Clothing and accessories',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Housewares and decor',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Personal care products',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Tickets for events and attractions',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Hobbies and recreation',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Gifts',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Charitable donations',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Professional fees',0,'2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_categories" VALUES('Other',0,'2026-10-23T14:56:09.010142+00:00');
CREATE TABLE finance_imports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            bank TEXT NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            imported_at_utc TEXT NOT NULL
        );
CREATE TABLE finance_merchant_rules(
            category TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            PRIMARY KEY(category, keyword)
        );
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','ENMAX','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','EPCOR','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','ATCO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','FORTIS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','DIRECT ENERGY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Electricity, gas and water','HYDRO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Internet, cable and home phone','SHAW CABLE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Internet, cable and home phone','SHAW CABLESYSTEMS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Mobile phone','TELUS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Mobile phone','ROGERS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Mobile phone','BELL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Mobile phone','FIDO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Mobile phone','KOODO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Streaming media subscriptions','NETFLIX','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Streaming media subscriptions','SPOTIFY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Streaming media subscriptions','DISNEY PLUS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Streaming media subscriptions','DISNEY+','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Streaming media subscriptions','CRAVE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','OPENAI','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','CHATGPT','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','GAMMA.APP','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','THETAWISE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','APPLE.COM/BILL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Other digital subscriptions','KOBO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','COSTCO GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','PETRO-CANADA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','PETRO CANADA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','SHELL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','ESSO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','MOBIL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','HUSKY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','CO-OP GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','COOP GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','CALG CO-OP GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','TSUU T''INA GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','TSUU T''INA NATI','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','SOUTHSIDE SER','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','FAS GAS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Gas and electric vehicle charging','CENTEX','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','COSTCO WHOLESALE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','COSTCO WHOLESAL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','SAFEWAY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','SOBEYS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','SAVE ON FOODS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','SAVE-ON-FOODS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','SUPERSTORE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','NO FRILLS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','FRESHCO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','WALMART','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','LOBLAWS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','REAL CANADIAN','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','T&T SUPERMARKET','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Groceries','T AND T','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','MCDONALD','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','WENDY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SUBWAY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','DOMINO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','CHIPOTLE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','DOORDASHCHIPOTLE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','KFC','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','POPEYES','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','BURGER KING','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','TIM HORTON','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','A&W','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','A & W','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','PIZZA HUT','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','COSMIC PIZZA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SENIORE''S PIZZA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SENIORE’S PIZZA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','JOEY','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','PORCH KITCHEN','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','BLOWERS AND GRAFTON','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','BLOWERS AND GRA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','CACTUS CLUB','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','LEOPOLDS TAVERN','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','HAYDEN BLOCK','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','FAHAD RESTAURAN','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','TURKISH KEBAB','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SUSHI','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SHAWARMA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','KOREAN BBQ','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','PHO 26','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','RESTAURANT','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','TAVERN','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','SMOKEHOUSE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','KITCHEN & COCKTA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','GRILL','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','BISTRO','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Restaurants (dine-in, delivery or takeout)','STEAKHOUSE','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Meal kits and food-delivery services','DOORDASHDASHPASS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Meal kits and food-delivery services','UBER EATS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Meal kits and food-delivery services','SKIPTHEDISHES','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Parking and tolls','UCALGARY PARKING','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Parking and tolls','HANGTAG PARKING','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Parking and tolls','INDIGO PARK','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Parking and tolls','PARKPLUS','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Clothing and accessories','FOOT LOCKER','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Clothing and accessories','SPORT CHEK','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Housewares and decor','RONA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Housewares and decor','HOME DEPOT','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Housewares and decor','IKEA','2026-10-23T14:56:09.010142+00:00');
INSERT INTO "finance_merchant_rules" VALUES('Charitable donations','ST MINA CHURCH','2026-10-23T14:56:09.010142+00:00');
CREATE TABLE finance_settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
INSERT INTO "finance_settings" VALUES('fixture-preserved','yes');
CREATE TABLE finance_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            bank TEXT NOT NULL,
            source_file TEXT NOT NULL,
            transaction_type TEXT NOT NULL DEFAULT 'Purchase',
            included INTEGER NOT NULL DEFAULT 1,
            note TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
INSERT INTO "finance_transactions" VALUES(1,'2026-10-01','Fixture groceries',12.34,'Groceries','Fixture bank','fixture.csv','Purchase',1,'','2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
CREATE TABLE grocery_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              default_unit TEXT NOT NULL DEFAULT 'item',
              aisle TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              UNIQUE(section_id, name),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE
            );
CREATE TABLE grocery_list_entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              grocery_item_id INTEGER NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              unit TEXT NOT NULL DEFAULT '',
              checked INTEGER NOT NULL DEFAULT 0,
              note TEXT NOT NULL DEFAULT '',
              added_by INTEGER NOT NULL,
              added_at_utc TEXT NOT NULL,
              checked_at_utc TEXT,
              UNIQUE(section_id, grocery_item_id),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE,
              FOREIGN KEY(added_by) REFERENCES users(id)
            );
CREATE TABLE grocery_price_history (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              grocery_item_id INTEGER NOT NULL,
              purchased_by INTEGER NOT NULL,
              store TEXT NOT NULL DEFAULT '',
              purchased_on TEXT NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              total_cost REAL NOT NULL,
              unit_cost REAL NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              created_at_utc TEXT NOT NULL,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE,
              FOREIGN KEY(purchased_by) REFERENCES users(id)
            );
CREATE TABLE grocery_recipe_ingredients (
              recipe_id INTEGER NOT NULL,
              grocery_item_id INTEGER NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              unit TEXT NOT NULL DEFAULT '',
              PRIMARY KEY(recipe_id, grocery_item_id),
              FOREIGN KEY(recipe_id) REFERENCES grocery_recipes(id) ON DELETE CASCADE,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE
            );
CREATE TABLE grocery_recipes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '',
              created_by INTEGER NOT NULL,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              UNIQUE(section_id, name),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('assignment','exam','lab')),
  title TEXT NOT NULL,
  notes TEXT,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
  priority INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 1 AND 5),
  weight REAL,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company TEXT NOT NULL,
  role TEXT NOT NULL,
  link TEXT,
  status TEXT NOT NULL DEFAULT 'interested'
    CHECK(status IN ('interested','applied','interview','offer','rejected')),
  applied_at_utc TEXT,
  followup_at_utc TEXT,
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE life_appearance (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            theme TEXT NOT NULL DEFAULT 'system',
            palette TEXT NOT NULL DEFAULT 'neutral',
            palette_style TEXT NOT NULL DEFAULT 'independent',
            updated_at TEXT NOT NULL
        );
INSERT INTO "life_appearance" VALUES(2,'dark','sage','full','2026-10-01T09:00:00+00:00');
CREATE TABLE life_calendar_connections (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider TEXT NOT NULL CHECK(provider IN ('google','microsoft','apple','ical')),
          label TEXT NOT NULL, external_id TEXT NOT NULL DEFAULT '',
          secret_blob TEXT NOT NULL, last_synced_at TEXT, last_error TEXT,
          created_at TEXT NOT NULL, last_sync_attempt_at TEXT, UNIQUE(user_id,provider,external_id)
        );
INSERT INTO "life_calendar_connections" VALUES(1,2,'google','Fixture calendar','','gAAAAABq23WJnlQoCksUuH9sAuYN2GvUao8kB02vzL2w-xtkA8pDs_dAKejSJK5Cre5zufA5eI5KvG76bUu9RUTFoGr4vxGtS8nQron70lrYy4LGvonBS8ablOfdNq4NhHbIEqcHaseYBrJpZCA3RI-Q9ikddONmWTTICVGfxUOpdLX8rbQ6XIE=','2026-10-01T09:00:00+00:00',NULL,'2026-10-01T09:00:00+00:00',NULL);
CREATE TABLE life_devices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          topic TEXT NOT NULL UNIQUE,
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        );
INSERT INTO "life_devices" VALUES(1,2,'Fixture phone','fixture-not-a-real-topic',0,'2026-10-01T09:00:00+00:00');
CREATE TABLE life_external_events (
          connection_id INTEGER NOT NULL REFERENCES life_calendar_connections(id) ON DELETE CASCADE,
          uid TEXT NOT NULL, title TEXT NOT NULL, starts_on TEXT NOT NULL,
          starts_at TEXT, href TEXT, calendar_name TEXT,
          PRIMARY KEY(connection_id,uid)
        );
INSERT INTO "life_external_events" VALUES(1,'fixture-event','Preserved cached event','2026-11-14','2026-11-14T12:00:00Z',NULL,NULL);
CREATE TABLE life_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE CASCADE,
          note_id INTEGER REFERENCES life_notes(id) ON DELETE CASCADE,
          filename TEXT NOT NULL, stored TEXT NOT NULL UNIQUE,
          size_bytes INTEGER NOT NULL, created_at TEXT NOT NULL,
          CHECK ((task_id IS NOT NULL)+(project_id IS NOT NULL)+(note_id IS NOT NULL)=1)
        );
INSERT INTO "life_files" VALUES(1,2,NULL,1,NULL,'preserved.txt','preserved-fixture.txt',45,'2026-10-01T09:00:00+00:00');
CREATE TABLE life_goals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, target_on TEXT, area TEXT NOT NULL DEFAULT 'Personal',
          status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','complete')),
          created_at TEXT NOT NULL
        );
CREATE TABLE life_habit_days (
          habit_id INTEGER NOT NULL REFERENCES life_habits(id) ON DELETE CASCADE,
          day TEXT NOT NULL, PRIMARY KEY(habit_id,day)
        );
CREATE TABLE life_habits (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, area TEXT NOT NULL DEFAULT 'Personal',
          created_at TEXT NOT NULL
        );
CREATE TABLE life_import_previews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          sha256 TEXT NOT NULL, rows_json TEXT NOT NULL,
          created_at TEXT NOT NULL, committed_at TEXT
        );
CREATE TABLE life_layouts (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            nav_order TEXT NOT NULL DEFAULT '[]', widget_order TEXT NOT NULL DEFAULT '[]',
            nav_labels TEXT NOT NULL DEFAULT '{}', nav_hidden TEXT NOT NULL DEFAULT '[]',
            widget_hidden TEXT NOT NULL DEFAULT '[]', widget_sizes TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL);
INSERT INTO "life_layouts" VALUES(2,'[]','[]','{"life-tasks": "My action list"}','[]','["money"]','{}','2026-10-01T09:00:00+00:00');
CREATE TABLE life_legacy_todo_map (
            todo_id INTEGER PRIMARY KEY,
            task_id INTEGER UNIQUE REFERENCES life_tasks(id) ON DELETE SET NULL,
            imported_at TEXT NOT NULL);
CREATE TABLE life_local_events (
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'meeting',
          location TEXT NOT NULL DEFAULT '', start_at_utc TEXT NOT NULL,
          end_at_utc TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
          created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL
        );
INSERT INTO "life_local_events" VALUES(1,2,'Preserved appointment','meeting','','2026-11-15T10:00:00+00:00','2026-11-15T11:00:00+00:00','','2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
CREATE TABLE life_notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT 'Personal',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
INSERT INTO "life_notes" VALUES(1,2,1,'Preserved note','Private body','Personal','2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
CREATE TABLE life_preferences (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          experience TEXT NOT NULL DEFAULT 'simple' CHECK(experience IN ('simple','guided','professional')),
          default_area TEXT NOT NULL DEFAULT 'Personal', created_at TEXT NOT NULL
        );
CREATE TABLE life_project_members (
          project_id INTEGER NOT NULL REFERENCES life_projects(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          role TEXT NOT NULL DEFAULT 'editor' CHECK(role IN ('viewer','editor')),
          PRIMARY KEY(project_id,user_id)
        );
INSERT INTO "life_project_members" VALUES(1,3,'editor');
INSERT INTO "life_project_members" VALUES(1,4,'viewer');
CREATE TABLE life_project_records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL REFERENCES life_projects(id) ON DELETE CASCADE,
          created_by INTEGER NOT NULL REFERENCES users(id),
          record_type TEXT NOT NULL CHECK(record_type IN ('milestone','risk','issue','decision','deliverable')),
          title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
          severity TEXT NOT NULL DEFAULT 'medium' CHECK(severity IN ('low','medium','high')),
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','monitor','resolved')),
          due_on TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
CREATE TABLE life_projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT 'Personal',
          color TEXT NOT NULL DEFAULT '#7285d5', template TEXT NOT NULL DEFAULT 'blank',
          status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','complete','archived')),
          due_on TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
INSERT INTO "life_projects" VALUES(1,2,'Preserved private course','','Study','#7285d5','blank','active',NULL,'2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
CREATE TABLE life_task_dependencies (
          task_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          depends_on_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          PRIMARY KEY(task_id,depends_on_id), CHECK(task_id != depends_on_id)
        );
CREATE TABLE life_task_notification_log (
          task_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          device_id INTEGER NOT NULL REFERENCES life_devices(id) ON DELETE CASCADE,
          due_day TEXT NOT NULL, sent_at TEXT NOT NULL,
          PRIMARY KEY(task_id,device_id,due_day)
        );
CREATE TABLE life_task_views (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          query_params TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
CREATE TABLE life_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          parent_id INTEGER REFERENCES life_tasks(id) ON DELETE CASCADE,
          title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','blocked','done')),
          priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
          area TEXT NOT NULL DEFAULT 'Personal', due_on TEXT,
          estimated_minutes INTEGER NOT NULL DEFAULT 0, recurrence TEXT NOT NULL DEFAULT 'none'
            CHECK(recurrence IN ('none','daily','weekly','monthly')),
          position INTEGER NOT NULL DEFAULT 0, completed_at TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
INSERT INTO "life_tasks" VALUES(1,2,1,NULL,'Preserved parent','','todo','normal','Study','2026-11-15',90,'none',0,NULL,'2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
INSERT INTO "life_tasks" VALUES(2,3,1,1,'Preserved child','','todo','normal','Personal',NULL,0,'none',0,NULL,'2026-10-01T09:00:00+00:00','2026-10-01T09:00:00+00:00');
CREATE TABLE life_time_entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE SET NULL,
          minutes INTEGER NOT NULL CHECK(minutes>0 AND minutes<=1440),
          note TEXT NOT NULL DEFAULT '', occurred_on TEXT NOT NULL, created_at TEXT NOT NULL
        );
INSERT INTO "life_time_entries" VALUES(1,2,1,NULL,30,'','2026-10-01','2026-10-01T09:00:00+00:00');
CREATE TABLE reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  remind_at_utc TEXT NOT NULL,
  message TEXT NOT NULL,
  sent_at_utc TEXT,
  created_at_utc TEXT NOT NULL
);
CREATE TABLE timers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              label TEXT NOT NULL,
              duration_seconds INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running','paused','done')),
              started_at_utc TEXT,
              remaining_seconds INTEGER,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              completed_at_utc TEXT, task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL, kind TEXT NOT NULL DEFAULT 'general',
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE TABLE todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  notes TEXT,
  due_at_utc TEXT,
  status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE COLLATE NOCASE,
              display_name TEXT NOT NULL DEFAULT '',
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin','member')),
              approved INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              approved_at_utc TEXT,
              approved_by INTEGER, email TEXT, email_verified INTEGER NOT NULL DEFAULT 0, auth_version INTEGER NOT NULL DEFAULT 1, must_change_password INTEGER NOT NULL DEFAULT 0, permissions_json TEXT NOT NULL DEFAULT '{}',
              FOREIGN KEY(approved_by) REFERENCES users(id)
            );
INSERT INTO "users" VALUES(1,'fixture_admin','fixture_admin','pbkdf2_sha256$310000$VmawWLBX2DMzj8a5KCzs9w==$2Db6EQS2f8XeT03jLbPe1jBXp7a0ip1kBoaD-FHUqxg=','admin',1,1,'2026-10-23T14:56:08.992945+00:00','2026-10-23T14:56:08.992965+00:00',NULL,NULL,0,1,0,'{}');
INSERT INTO "users" VALUES(2,'alice','alice','pbkdf2_sha256$310000$DIPGInmnA7mu4NSMAJBukw==$J6nL6cdYzNobguGju0Vy_ECUSkn1R4HbEzq4fru8X90=','member',1,1,'2026-10-23T14:56:09.373819+00:00',NULL,NULL,'alice@example.test',1,1,0,'{}');
INSERT INTO "users" VALUES(3,'editor','editor','pbkdf2_sha256$310000$W8eLiTUtuwuYwOsaeDCyHw==$HImD9ngAFphTYN93SLLVF5xidp4fVXqCvRJ5cJAVW94=','member',1,1,'2026-10-23T14:56:09.542903+00:00',NULL,NULL,'editor@example.test',1,1,0,'{}');
INSERT INTO "users" VALUES(4,'viewer','viewer','pbkdf2_sha256$310000$L3FepcP-QQmBC7j5xZLMnw==$ayhbtd_EMXgnD1sJ8OJeBLWlgi5hH8iyBEaqpeid7LY=','member',1,1,'2026-10-23T14:56:09.647503+00:00',NULL,NULL,'viewer@example.test',1,1,0,'{"projects_create": false}');
INSERT INTO "users" VALUES(5,'pending','pending','pbkdf2_sha256$310000$xNnVcp6BlRIOHG1dgeSSuA==$79LDrB6iHg1mME1KZqR4tyL0aeSm2PCMxzvVRe4FOc4=','member',0,1,'2026-10-23T14:56:09.786446+00:00',NULL,NULL,'pending@example.test',0,1,0,'{}');
CREATE TABLE workspace_checklist_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              content TEXT NOT NULL,
              checked INTEGER NOT NULL DEFAULT 0,
              position INTEGER NOT NULL DEFAULT 0,
              created_by INTEGER NOT NULL,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
CREATE TABLE workspace_section_members (
              section_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              can_edit INTEGER NOT NULL DEFAULT 1,
              added_at_utc TEXT NOT NULL,
              PRIMARY KEY(section_id, user_id),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE TABLE workspace_sections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              icon TEXT NOT NULL DEFAULT '📄',
              description TEXT NOT NULL DEFAULT '',
              section_type TEXT NOT NULL DEFAULT 'blank' CHECK(section_type IN ('blank','grocery')),
              content TEXT NOT NULL DEFAULT '',
              show_in_sidebar INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE INDEX idx_reminders_due ON reminders(sent_at_utc, remind_at_utc);
CREATE INDEX idx_reminders_entity ON reminders(entity_type, entity_id);
CREATE INDEX idx_todos_status_due ON todos(status, due_at_utc);
CREATE INDEX idx_expenses_due ON expenses(status, due_at_utc);
CREATE INDEX idx_users_approval ON users(approved, active, created_at_utc);
CREATE UNIQUE INDEX idx_users_email_unique ON users(lower(email)) WHERE email IS NOT NULL AND email != '';
CREATE INDEX idx_auth_email_tokens_user ON auth_email_tokens(user_id,purpose,created_at);
CREATE UNIQUE INDEX idx_finance_transactions_unique
        ON finance_transactions(date, description, amount, bank, source_file)
        ;
CREATE INDEX idx_finance_transactions_date
        ON finance_transactions(date)
        ;
CREATE INDEX idx_finance_transactions_category
        ON finance_transactions(category)
        ;
CREATE INDEX idx_workspace_sections_owner ON workspace_sections(owner_user_id, updated_at_utc);
CREATE INDEX idx_grocery_prices_item_date ON grocery_price_history(grocery_item_id, purchased_on DESC, id DESC);
CREATE INDEX idx_timers_user_status ON timers(user_id,status,updated_at_utc DESC);
CREATE INDEX life_projects_owner ON life_projects(owner_id,status,updated_at DESC);
CREATE INDEX life_members_user ON life_project_members(user_id,project_id);
CREATE INDEX life_tasks_owner_due ON life_tasks(owner_id,status,due_on);
CREATE INDEX life_tasks_project_status ON life_tasks(project_id,status,position);
CREATE INDEX life_project_records_project ON life_project_records(project_id,record_type,status);
CREATE INDEX life_notes_owner ON life_notes(owner_id,updated_at DESC);
CREATE INDEX life_time_owner ON life_time_entries(owner_id,occurred_on DESC);
CREATE INDEX idx_task_views_user ON life_task_views(user_id,id DESC);
CREATE INDEX idx_mlo_items_due ON items(due_at_utc);
CREATE INDEX idx_mlo_events_start ON events(start_at_utc);
CREATE INDEX idx_mlo_jobs_followup ON jobs(followup_at_utc);
CREATE INDEX idx_mlo_tasks_owner_created ON life_tasks(owner_id,created_at DESC);
CREATE INDEX idx_mlo_tasks_owner_area ON life_tasks(owner_id,area,status);
CREATE INDEX idx_mlo_time_day ON life_time_entries(owner_id,occurred_on);
CREATE INDEX life_cal_connections_user ON life_calendar_connections(user_id);
CREATE INDEX life_local_events_user_start ON life_local_events(user_id,start_at_utc);
CREATE INDEX life_external_events_day ON life_external_events(starts_on);
CREATE INDEX life_devices_owner ON life_devices(owner_id);
CREATE INDEX idx_life_imports_owner ON life_import_previews(owner_id,created_at DESC);
CREATE INDEX life_files_task ON life_files(task_id);
CREATE INDEX life_files_project ON life_files(project_id);
CREATE INDEX life_files_note ON life_files(note_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('users',5);
INSERT INTO "sqlite_sequence" VALUES('life_projects',1);
INSERT INTO "sqlite_sequence" VALUES('life_tasks',2);
INSERT INTO "sqlite_sequence" VALUES('life_notes',1);
INSERT INTO "sqlite_sequence" VALUES('life_time_entries',1);
INSERT INTO "sqlite_sequence" VALUES('life_devices',1);
INSERT INTO "sqlite_sequence" VALUES('finance_transactions',1);
INSERT INTO "sqlite_sequence" VALUES('life_files',1);
COMMIT;
