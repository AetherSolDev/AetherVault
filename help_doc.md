# 🔑 KISS Python Password Manager Documentation

**KISS** stands for **K**eep **I**t **S**imple & **S**ecure. This application is a portable, local password vault designed for maximum security and ease of use.

## I. ✨ Core Features

* **AES-256 Encryption:** All credentials are encrypted using industry-standard AES-256 cipher derived from your Master Password, ensuring data is secure while at rest.
* **Portable Data:** Your entire vault is stored in a single encrypted database file (`password_manager.db`), making it easy to back up and move across different locations (e.g., a USB drive).
* **Automatic Backup:** The application automatically creates a backup of your database (`password_manager.db.bak`) every time you save a new entry and when you close the application.
* **Auto-Lock Security:** The application automatically locks itself after a configurable period of inactivity (default is 3 minutes), requiring your Master Password to regain access.
* **Strong Password Generator:** Quickly generate complex, randomized passwords to maximize the security of your accounts.
* **Data Management:** Tools for secure CSV Export, Import, and Duplicate Removal.

## II. 🚀 Getting Started

### 1. Initial Setup
The first time you run the application, you will be prompted to **Set Your Master Password**.

* Choose a strong, unique password. This is the **only** password you will need to remember.
* The Master Password is used to encrypt your entire vault. **Without it, your data is permanently inaccessible.**

### 2. Login
On subsequent starts, you will use your Master Password to decrypt and access your vault.

### 3. Adding a New Entry
1.  Click the **New Entry** button or use `File > New Entry`.
2.  Fill in the **Title** and **Password** (these are required).
3.  Optional: Use the **Generate Password** button to create a strong password.
4.  Click **Save**. The entry is immediately encrypted and stored.

## III. 💡 Usage Guide

### A. The Credential Form
| Field | Purpose |
| :--- | :--- |
| **Title** | The unique name for the service (e.g., "Google Mail"). |
| **Password** | The stored credential. |
| **URL** | The website address for easy reference. |
| **Username/Email** | The associated login ID. |
| **Notes** | For security questions, recovery codes, or other details. |

### B. Quick Actions
* **Copy Buttons:** Next to the Password, Username, and Email fields, these buttons copy the value to your clipboard. The clipboard is **automatically cleared** after 10 seconds for security.
* **Search:** Use the search bar at the top to filter the list instantly by Title, Username, or URL.

### C. Password Generator
1.  Click the **Generate Password** button on the form.
2.  Adjust the length and character sets (Uppercase, Numbers, Symbols).
3.  The generated password appears in the preview box.
4.  Click **Use Password** to copy it into the main password field.

## IV. ⚙️ Data Management & Recovery

**ALWAYS** keep multiple copies of your database file for safety.

### 1. Backup & Restore
* **Auto-Backup:** A backup file (`password_manager.db.bak`) is created automatically in the same folder as the main database.
* **Manual Backup (`File > Manual Backup`):** Creates an immediate backup.
* **Restoring Data:** If your main database file (`password_manager.db`) is corrupted or lost, simply rename the backup file (`password_manager.db.bak`) to `password_manager.db` while the application is closed.

### 2. Import / Export (`File` Menu)
* **Export to CSV:** Creates an unencrypted text file (`credentials_export.csv`) containing all your data. **Handle this file with extreme care, as it is NOT encrypted.**
* **Import from CSV:** Allows you to load data from a compatible CSV file. This is useful for migrating data from other managers.

#### 3. Duplicate Removal (`Tools > Remove Duplicates`)
This feature scans your vault and removes entries that share the same **Title** and **Username**. When a duplicate is found, the tool **keeps the newest entry** (based on the modification date) and deletes the older entry. This ensures that updates from re-imports are always preserved.

**CRITICAL SAFETY NOTE:** A timestamped backup (`kiss_vault_...db.bak`) is created before running this tool, allowing you to easily roll back if necessary..

## V. ⚠️ Troubleshooting & Security

### 1. Master Password Reset
**IT IS NOT POSSIBLE TO RECOVER OR RESET YOUR MASTER PASSWORD.** The password is not stored; only its secure hash is used to derive the encryption key. If you forget it, the data in the vault is permanently locked.

### 2. Data File Locations
All key application files are stored in the same directory as the executable:
* **Vault:** `password_manager.db` (Encrypted)
* **Backup:** `password_manager.db.bak` (Encrypted)
* **Master Key Hash:** `.master.key` (Secured Hash)
* **Settings:** `.app_settings.json` (Unencrypted configuration)

### 3. Auto-Lock Customization
Go to **Tools > Settings** to adjust the automatic lock-out time (in minutes). Select `0` to disable auto-lock.
