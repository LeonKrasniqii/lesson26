import sqlite3
import threading
import time
import requests
import streamlit as st
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# ================= Database =================
DB_NAME = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ================= Pydantic Models =================
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    completed: bool

# ================= FastAPI App =================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/tasks/", response_model=List[Task])
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [Task(id=row["id"], title=row["title"], description=row["description"], completed=bool(row["completed"])) for row in rows]

@app.post("/tasks/", response_model=Task)
def create_task(task: TaskCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (task.title, task.description)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return Task(id=task_id, title=task.title, description=task.description, completed=False)

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, completed: bool):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (int(completed), task_id))
    conn.commit()
    conn.close()
    return Task(id=row["id"], title=row["title"], description=row["description"], completed=completed)

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"detail": "Task deleted"}

# ================= Run FastAPI in Thread =================
def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000)

api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()
time.sleep(1)  # Give API a second to start

# ================= Streamlit Frontend =================
st.title("Task Manager App (All-in-One)")

API_URL = "http://127.0.0.1:8000"

if "tasks_updated" not in st.session_state:
    st.session_state.tasks_updated = True  # force first load

def load_tasks():
    response = requests.get(f"{API_URL}/tasks/")
    if response.status_code == 200:
        return response.json()
    return []

# --------- Add Task ---------
st.header("Add a New Task")
with st.form("add_task_form"):
    title = st.text_input("Title")
    description = st.text_input("Description")
    submitted = st.form_submit_button("Add Task")
    if submitted:
        if title:
            requests.post(f"{API_URL}/tasks/", json={"title": title, "description": description})
            st.session_state.tasks_updated = True
        else:
            st.warning("Title is required")

# --------- Display Tasks ---------
st.header("All Tasks")
tasks = load_tasks() if st.session_state.tasks_updated else []
st.session_state.tasks_updated = False

for task in tasks:
    col1, col2, col3, col4 = st.columns([3, 4, 2, 2])
    col1.write(task["title"])
    col2.write(task["description"] or "")

    completed_checkbox = col3.checkbox("Completed", value=task["completed"], key=f"chk{task['id']}")
    if completed_checkbox != task["completed"]:
        requests.put(f"{API_URL}/tasks/{task['id']}", params={"completed": completed_checkbox})
        st.session_state.tasks_updated = True

    delete_button = col4.button("Delete", key=f"del{task['id']}")
    if delete_button:
        requests.delete(f"{API_URL}/tasks/{task['id']}")
        st.session_state.tasks_updated = True

# Reload tasks if any update happened
if st.session_state.tasks_updated:
    st.experimental_rerun()
