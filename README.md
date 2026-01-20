


# 🏥 MediSync: Hospital Resource Planning & Emergency Response System

![MediSync Status](https://img.shields.io/badge/Status-Hackathon_Finalist-success?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI_|_TiDB_|_WebSockets-blue?style=for-the-badge)

> **Connecting Ambulances, Hospitals, and Patients in milliseconds.**

## 🚨 The Problem
In critical medical emergencies, **time is the enemy**.
1.  **Ambulances** drive blindly to hospitals without knowing real-time bed availability.
2.  **Receptionists** are overwhelmed during patient surges, leading to triage errors.
3.  **Doctors** lack visibility into live inventory (oxygen/meds) while treating patients.
4.  **Patients** have no transparency regarding their wait time or queue status.

## 💡 The Solution
**MediSync** is a unified city-wide ERP system that synchronizes data across all stakeholders. It features a **WebSocket-based Emergency Alert System** that allows ambulances to notify hospitals *before* arrival, ensuring trauma teams are ready.

---

## 🌟 Key Features

### 🚑 1. Ambulance Command (Mobile-First)
* **Geo-Location Search:** Find nearest hospitals filtered by bed availability.
* **Smart Routing:** Automatically **disables alerts** for hospitals with **0 ICU Beds** to prevent patient dumping.
* **One-Tap Panic Button:** Sends a high-priority "Red Alert" signal to the destination hospital.

### 📝 2. Receptionist Console
* **Flash Alerts:** Screen flashes **RED** with a siren effect when an ambulance is incoming.
* **Digital Triage:** Auto-calculates a "Priority Score" (Severity 1-10) to sort the waiting list dynamically.

### 👨‍⚕️ 3. Doctor Dashboard
* **Live Bed Management:** Discharge or transfer patients (ICU ↔ General) with one click.
* **Integrated Pharmacy:** Dispense meds directly from the dashboard; updates global inventory instantly.

### 🏥 4. Hospital Admin
* **Analytics Dashboard:** Visual graphs of Bed Occupancy and Queue trends.
* **Inventory Alerts:** Auto-alerts when Oxygen or critical meds drop below safe thresholds.

### 🌍 5. Public Portal
* **City-Wide Vacancy:** Real-time transparency on bed availability across all registered hospitals in the city.

---

## 🛠️ Tech Stack

* **Backend:** Python (FastAPI) - High-performance `async` capabilities.
* **Database:** MySQL / TiDB (via SQLAlchemy) - ACID compliance for medical data integrity.
* **Real-Time:** WebSockets - Sub-second latency for Emergency Alerts.
* **Frontend:** HTML5, CSS3, Vanilla JS - Lightweight & optimized for low-end devices.
* **Templating:** Jinja2 - Secure Server-Side Rendering (SSR).

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/medisync.git](https://github.com/yourusername/medisync.git)
cd medisync

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Configure Environment

Create a `.env` file in the root directory:

```env
DATABASE_URL="mysql+aiomysql://user:password@localhost/medisync_db"
SECRET_KEY="supersecretkey123"

```

### 4. Run the Server

```bash
uvicorn app.main:app --reload

```

*Access the app at: `http://127.0.0.1:8000*`

### 5. Initialize Demo Data (CRITICAL)

To avoid manual data entry, we have built a **Master Seed** script.

1. Go to `http://127.0.0.1:8000/docs`
2. Find **POST /seed/master-reset**
3. Click **Execute**
4. *(Optional)* Run **POST /seed/add-full-hospital** to simulate a 100% full facility.

---

## 🔐 Demo Credentials (Cheat Sheet)

**Master Password for ALL accounts:** `123`

| Role | Username | Dashboard Features |
| --- | --- | --- |
| **Ambulance** | `driver1` | Search hospitals, Send Alerts (Try sending to "City General") |
| **Receptionist** | `reception1` | Receives Alert (Pop-up), Triage Registration |
| **Doctor** | `doc1` | Admit from Queue, Transfer Bed, Dispense Meds |
| **Hosp Admin** | `admin1` | View Inventory, Analytics Graphs |
| **Patient** | `patient1` | View Status (Home/Queue/Admitted) |
| **Super Admin** | `superadmin` | Create new hospitals |

> **Pro Tip:** For the best demo effect, log in as `driver1` on your phone and `reception1` on your laptop to show the instant sync!

---

## 🔮 Future Scope

* **IoT Integration:** Sensors in Oxygen tanks to auto-update DB levels.
* **AI Bed Prediction:** ML model to predict shortages based on seasonal flu trends.
* **SMS Gateway:** Send text updates to patient families regarding status changes.

---

## 👥 Team Binary Beasts

* **Veer Dodiya** - Team Leader & Full Stack Dev
* **Nirjal Jagtap** - Frontend & Design
* **Hrishikesh Ganji** - Database & Analytics
* **Chinmay Chopade** - PPT and UI/UX

---

**Made with ❤️ for CSI-TSEC Rubix Hackathon '26**
