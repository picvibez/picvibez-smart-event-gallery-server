# 🚀 FastAPI Starter Project

A simple FastAPI project with a virtual environment setup and basic API endpoints.

---

## 📦 Requirements

* Python 3.8+
* pip (Python package manager)

---

## ⚙️ Setup Instructions

### 1️⃣ Clone or Create Project Folder

```bash
mkdir fastapi-project
cd fastapi-project
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

---

### 3️⃣ Activate Virtual Environment

#### 🪟 Windows:

```bash
venv\Scripts\activate
```

#### 🍎 Mac/Linux:

```bash
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```bash
pip install fastapi uvicorn
```

---

### 5️⃣ Create Main File

Create a file named `main.py` and add:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello FastAPI 🚀"}

@app.get("/add")
def add(a: int, b: int):
    return {"result": a + b}
```

---

### 6️⃣ Run the Server

```bash
python -m uvicorn main:app --reload
```

---

## 🌐 API Endpoints

| Endpoint       | Description     |
| -------------- | --------------- |
| `/`            | Home route      |
| `/add?a=1&b=2` | Add two numbers |

---

## 📘 Interactive Docs

Once the server is running, open:

* Swagger UI: http://127.0.0.1:8000/docs
* ReDoc: http://127.0.0.1:8000/redoc

---

## 🧠 Project Structure

```
fastapi-project/
│
├── venv/          # Virtual environment
├── main.py        # Main application
└── README.md      # Project documentation
```

---

## 🛑 Deactivate Virtual Environment

```bash
deactivate
```

---

## 💡 Notes

* Always use a virtual environment for projects
* Use `requirements.txt` for managing dependencies

---

## 📄 License

This project is for learning purposes.
