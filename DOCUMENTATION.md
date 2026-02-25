# CampusPro Management System - Technical Documentation

Welcome to the **CampusPro** documentation. This system is a modern, Flask-based school management platform designed for institutions requiring robust student/faculty tracking and enterprise-grade analytics.

## 1. System Overview
The system is built using:
- **Backend**: Python Flask with SQLAlchemy (SQLite for default storage).
- **Frontend**: Tailwind CSS (SaaS UI System), Lucide Icons, Chart.js.
- **Architecture**: Modular blueprint structure for scalability.

## 2. Core Modules

### 2.1 User Management
- **Roles**: Admin, Teacher, Student, Parent.
- **Access Control**: Handled via the `@role_required` decorator.
- **Profiles**: Comprehensive data storage including contact info, addresses, and role-specific metadata.

### 2.2 Academic Directory (Admin Only)
- **Faculty**: Add/Edit/Delete teachers. Pro users have unlimited faculty slots.
- **Students**: Register students, assign them to classes, and link them to parents.
- **Classes**: Define academic groups (e.g., Grade 10A).
- **Subjects**: Design the curriculum and assign instructors to specific classes.

### 2.3 Pro System & Monetization
The system includes a **Pro Upgrade ($100/year)** feature gated by the `@pro_required` decorator.
- **Unlocking**: Click "Upgrade Now" in the sidebar and complete a simulated payment.
- **Features Unlocked**:
  - **Advanced Analytics**: Interactive charts showing academic trends.
  - **Unlimited Capacity**: Removes limits on student/teacher registration.
  - **Export Tools**: CSV/Excel downloads for all records.
  - **System Backups**: One-click JSON database backups.

### 2.4 Messaging Center
Internal communication system allowing users to send and receive messages within the platform.

## 3. Financial Management
Managed under the `Financials` tab.
- **Fees**: Admins can create various fee types (Tuition, Lab, etc.).
- **Payments**: Track status (Paid, Pending, Partial) and generate receipts.

## 4. Pro-Only Advanced Features

### 4.1 Analytics Hub
Utilizes Chart.js to visualize:
- Academic performance trends over time.
- Enrollment vs. capacity ratios.
- Faculty efficiency rankings based on score averages.

### 4.2 Automated Reporting
Gated features allowing admins to generate bulk reports for students and financial audits.

## 5. Security Protocols
- **Passwords**: All passwords are hashed using `pbkdf2:sha256` via Werkzeug.
- **Session Security**: Routes are protected by login requirements.
- **Pro Gating**: Sensitive routes check `user.is_pro` status server-side to prevent URL hacking.

## 6. How to Upgrade
1. Navigate to the `Upgrade` page.
2. Select your payment method:
   - **Stripe/PayPal**: Standard international payments.
   - **MTN/Orange Money**: Optimized for Cameroon-based institutions.
   - **Bank Transfer**: Manual verification required by Admin.
3. Upon success, the `is_pro` flag is set in the database, and the UI dynamically updates to show the Pro Badge.

---
*Created with ❤️ by the CampusPro Development Team.*
